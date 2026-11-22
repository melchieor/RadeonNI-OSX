/* Offscreen GL upload/render/readback comparison. No driver/config writes. MIT */
#include <OpenGL/OpenGL.h>
#include <OpenGL/CGLRenderers.h>
#include <OpenGL/gl.h>
#include <OpenGL/glext.h>
#include <stdio.h>
#include <stdint.h>
#include <stdlib.h>
#include <string.h>
#include <sys/stat.h>
#include <errno.h>
#include "pixel-reference.h"
#ifndef TW
#define TW 64
#endif
#ifndef TH
#define TH 32
#endif
#define W (TW-1)
#define H (TH-1)
#define UPLOAD_ROW (TW+16)
#define ROW_BYTES_APPLE 0x8A16
static const char *output;
static unsigned tests,failures,skips,pending_case_errors;
/* Spare readback space catches common erroneous padded-row writes without
   immediately corrupting adjacent state. A damaged guard stops GPU cases. */
static unsigned char expected[TW*TH*4],read_tex[TW*TH*4+65536],rendered[W*H*4+65536],reference[W*H*4];
static int damaged_readback;
static unsigned legacy_readback_kind;
static unsigned char texture_reference[TW*TH*4];
static unsigned char upload[UPLOAD_ROW*(TH+4)*4+64];
static GLuint textures[3],fbo,pbo;
static int rowbytes_supported,rectangle_supported,pbo_supported;
static GLenum bound_target;
static int ppm(const char *name,const unsigned char *pixels,unsigned width,unsigned height)
{
 char path[1024];if(snprintf(path,sizeof(path),"%s/%s.ppm",output,name)>=(int)sizeof(path))return 0;
 FILE *fp=fopen(path,"wb");if(!fp){perror(path);return 0;}
 fprintf(fp,"P6\n%u %u\n255\n",width,height);
 for(unsigned row=height;row>0;row--)for(unsigned x=0;x<width;x++)
  if(fwrite(pixels+((row-1)*width+x)*4,1,3,fp)!=3){fclose(fp);return 0;}
 if(fclose(fp))return 0;
 if(snprintf(path,sizeof(path),"%s/%s.rgba",output,name)>=(int)sizeof(path))return 0;
 fp=fopen(path,"wb");if(!fp){perror(path);return 0;}
 if(fwrite(pixels,4,width*height,fp)!=width*height){perror("RGBA write");fclose(fp);return 0;}
 return fclose(fp)==0;
}
static unsigned compare(const char *name,const char *stage,const unsigned char *want,const unsigned char *actual,unsigned count,unsigned width)
{
 unsigned wrong=0,max_error=0,alpha_wrong=0;
 for(unsigned i=0;i<count;i++){
  int bad=0;
  for(unsigned k=0;k<4;k++){
   unsigned a=want[i*4+k],b=actual[i*4+k],d=a>b?a-b:b-a;
   if(d>max_error)max_error=d;
   if(d>1){bad=1;if(k==3)alpha_wrong++;}
  }
  if(bad){
   if(wrong<4)printf("  %s/%s at (%u,%u) expected=%u,%u,%u,%u actual=%u,%u,%u,%u\n",name,stage,i%width,i/width,
    want[i*4],want[i*4+1],want[i*4+2],want[i*4+3],actual[i*4],actual[i*4+1],actual[i*4+2],actual[i*4+3]);
   wrong++;
  }
 }
 printf("%s %s mismatched_pixels=%u/%u alpha_mismatches=%u max_channel_error=%u tolerance=1\n",name,stage,wrong,count,alpha_wrong,max_error);
 return wrong;
}
static void reset_unpack(void)
{
 if(pbo_supported)glBindBuffer(GL_PIXEL_UNPACK_BUFFER,0);
 glPixelStorei(GL_UNPACK_ALIGNMENT,1);glPixelStorei(GL_UNPACK_ROW_LENGTH,0);
 glPixelStorei(GL_UNPACK_SKIP_PIXELS,0);glPixelStorei(GL_UNPACK_SKIP_ROWS,0);glPixelStorei(GL_UNPACK_SWAP_BYTES,GL_FALSE);
 if(rowbytes_supported)glPixelStorei(ROW_BYTES_APPLE,0);
}
static void fill_upload(unsigned phase,unsigned row_pixels,unsigned skip_x,unsigned skip_y,int packed,unsigned prefix)
{
 memset(upload,0xc7,sizeof(upload));
 for(unsigned y=0;y<TH;y++)for(unsigned x=0;x<TW;x++){
  unsigned char rgba[4];pixel_source(x,y,phase,rgba);
  unsigned char *dst=upload+prefix+((y+skip_y)*row_pixels+x+skip_x)*4;
  if(packed){uint32_t word=pixel_bgra_rev(rgba);memcpy(dst,&word,4);}else memcpy(dst,rgba,4);
 }
}
static void fill_expected(unsigned phase)
{for(unsigned y=0;y<TH;y++)for(unsigned x=0;x<TW;x++)pixel_source(x,y,phase,expected+(y*TW+x)*4);}
static void select_texture(GLenum target)
{
 bound_target=target;glDisable(GL_TEXTURE_2D);if(rectangle_supported)glDisable(GL_TEXTURE_RECTANGLE_ARB);
 glEnable(target);glBindTexture(target,textures[target==GL_TEXTURE_2D?0:1]);
}
static unsigned check_case(const char *name,int blend)
{
 unsigned bad=pending_case_errors;pending_case_errors=0;char path[160];
 if(pbo_supported){glBindBuffer(GL_PIXEL_UNPACK_BUFFER,0);glBindBuffer(GL_PIXEL_PACK_BUFFER,0);}
 glPixelStorei(GL_PACK_ALIGNMENT,1);glPixelStorei(GL_PACK_ROW_LENGTH,0);glPixelStorei(GL_PACK_SKIP_PIXELS,0);glPixelStorei(GL_PACK_SKIP_ROWS,0);
 glViewport(0,0,W,H);glDisable(GL_DITHER);glDisable(GL_SCISSOR_TEST);glDisable(GL_DEPTH_TEST);glDisable(GL_STENCIL_TEST);glDisable(GL_ALPHA_TEST);
 glColorMask(GL_TRUE,GL_TRUE,GL_TRUE,GL_TRUE);
 glDisable(GL_BLEND);glClearColor(37.0f/255,71.0f/255,109.0f/255,1);glClear(GL_COLOR_BUFFER_BIT);
 if(blend){glEnable(GL_BLEND);glBlendFunc(GL_ONE,GL_ONE_MINUS_SRC_ALPHA);}
 glMatrixMode(GL_PROJECTION);glLoadIdentity();glOrtho(0,W,0,H,-1,1);
 glMatrixMode(GL_MODELVIEW);glLoadIdentity();glTexEnvi(GL_TEXTURE_ENV,GL_TEXTURE_ENV_MODE,GL_REPLACE);
 float sx=bound_target==GL_TEXTURE_2D?(float)W/TW:W;
 float sy=bound_target==GL_TEXTURE_2D?(float)H/TH:H;
 glBegin(GL_QUADS);
 glTexCoord2f(0,0);glVertex2f(0,0);glTexCoord2f(sx,0);glVertex2f(W,0);
 glTexCoord2f(sx,sy);glVertex2f(W,H);glTexCoord2f(0,sy);glVertex2f(0,H);glEnd();
 /* No explicit finish or texture read before drawing: observe normal GL ordering. */
 memset(rendered,0xcd,sizeof(rendered));glReadPixels(0,0,W,H,GL_RGBA,GL_UNSIGNED_BYTE,rendered);
 for(unsigned y=0;y<H;y++)for(unsigned x=0;x<W;x++)pixel_blend(expected+(y*TW+x)*4,blend,reference+(y*W+x)*4);
 bad+=compare(name,"render",reference,rendered,W*H,W);
 memset(read_tex,0xcd,sizeof(read_tex));glGetTexImage(bound_target,0,GL_RGBA,GL_UNSIGNED_BYTE,read_tex);
 for(unsigned i=0;i<TW*TH;i++)pixel_texture_readback(expected+i*4,legacy_readback_kind,texture_reference+i*4);
 bad+=compare(name,"texture",texture_reference,read_tex,TW*TH,TW);
 for(unsigned i=W*H*4;i<sizeof(rendered);i++)if(rendered[i]!=0xcd){printf("%s GUARD_DAMAGE render byte=%u\n",name,i);bad++;damaged_readback=1;break;}
 for(unsigned i=TW*TH*4;i<sizeof(read_tex);i++)if(read_tex[i]!=0xcd){printf("%s GUARD_DAMAGE texture byte=%u\n",name,i);bad++;damaged_readback=1;break;}
 for(unsigned n=0;n<8;n++){GLenum error=glGetError();if(!error)break;printf("%s GL_ERROR=0x%x\n",name,error);bad++;}
 snprintf(path,sizeof(path),"%s-expected",name);if(!ppm(path,reference,W,H))bad++;
 snprintf(path,sizeof(path),"%s-rendered",name);if(!ppm(path,rendered,W,H))bad++;
 snprintf(path,sizeof(path),"%s-texture",name);if(!ppm(path,read_tex,TW,TH))bad++;
 snprintf(path,sizeof(path),"%s-texture-expected",name);if(!ppm(path,texture_reference,TW,TH))bad++;
 unsigned char diff[W*H*4];
 for(unsigned i=0;i<W*H;i++){
  int mismatch=0;for(unsigned k=0;k<4;k++){int d=(int)reference[i*4+k]-rendered[i*4+k];if(d>1||d< -1)mismatch=1;}
  diff[i*4]=diff[i*4+2]=mismatch?255:0;diff[i*4+1]=0;diff[i*4+3]=255;
 }
 snprintf(path,sizeof(path),"%s-diff",name);if(!ppm(path,diff,W,H))bad++;
 tests++;if(bad)failures++;
 printf("CASE %s %s\n",name,bad?"FAIL":"PASS");return bad;
}
static void full_case(const char *name,GLenum target,unsigned phase,int packed,int padded,int use_pbo,int use_rowbytes,int blend,int define)
{
 select_texture(target);reset_unpack();fill_expected(phase);
 unsigned row=padded?UPLOAD_ROW:TW,skip_x=padded?3:0,skip_y=padded?2:0,prefix=use_pbo?64:0;
 fill_upload(phase,row,skip_x,skip_y,packed,prefix);
 glPixelStorei(GL_UNPACK_ROW_LENGTH,row);glPixelStorei(GL_UNPACK_SKIP_PIXELS,skip_x);glPixelStorei(GL_UNPACK_SKIP_ROWS,skip_y);
 if(use_rowbytes){glPixelStorei(GL_UNPACK_ROW_LENGTH,0);glPixelStorei(ROW_BYTES_APPLE,row*4);}
 const void *pointer=upload;
 if(use_pbo){
  glBindBuffer(GL_PIXEL_UNPACK_BUFFER,pbo);glBufferData(GL_PIXEL_UNPACK_BUFFER,sizeof(upload),upload,GL_STREAM_DRAW);
  GLint binding=0;glGetIntegerv(GL_PIXEL_UNPACK_BUFFER_BINDING,&binding);GLenum error=glGetError();
  if(error || (GLuint)binding!=pbo){printf("CASE %s FAIL PBO setup error=0x%x binding=%u\n",name,error,(unsigned)binding);tests++;failures++;reset_unpack();return;}
  pointer=(void*)(uintptr_t)prefix;
 }
 if(define)glTexImage2D(target,0,GL_RGBA8,TW,TH,0,packed?GL_BGRA:GL_RGBA,packed?GL_UNSIGNED_INT_8_8_8_8_REV:GL_UNSIGNED_BYTE,pointer);
 else glTexSubImage2D(target,0,0,0,TW,TH,packed?GL_BGRA:GL_RGBA,packed?GL_UNSIGNED_INT_8_8_8_8_REV:GL_UNSIGNED_BYTE,pointer);
 reset_unpack();check_case(name,blend);
}
/* Single/two-channel glyph formats omitted by the original RGBA probe. */
static void glyph_formats(void)
{
 const GLenum formats[]={GL_ALPHA,GL_LUMINANCE,GL_LUMINANCE_ALPHA,GL_RGB};
 const GLint internal[]={GL_ALPHA8,GL_LUMINANCE8,GL_LUMINANCE8_ALPHA8,GL_RGB8};
 const char *names[]={"glyph-alpha8","glyph-luminance8","glyph-luminance-alpha8","glyph-rgb8"};
 select_texture(GL_TEXTURE_2D);reset_unpack();
 for(unsigned pass=0;pass<4 && !damaged_readback;pass++){
  unsigned components=pass==2?2:pass==3?3:1;
  memset(upload,0xc7,sizeof(upload));
  for(unsigned y=0;y<TH;y++)for(unsigned x=0;x<TW;x++){
   unsigned char rgba[4];pixel_source(x,y,5,rgba);unsigned char a=rgba[3],l=(x*17+y*13)&255;
   unsigned char *src=upload+(y*TW+x)*components,*dst=expected+(y*TW+x)*4;
   if(pass==0){src[0]=a;dst[0]=dst[1]=dst[2]=255;dst[3]=a;}
   else if(pass==1){src[0]=l;dst[0]=dst[1]=dst[2]=l;dst[3]=255;}
   else if(pass==2){src[0]=l;src[1]=a;dst[0]=dst[1]=dst[2]=l;dst[3]=a;}
   else {src[0]=dst[0]=l;src[1]=dst[1]=a;src[2]=dst[2]=255-l;dst[3]=255;}
  }
  glTexImage2D(GL_TEXTURE_2D,0,internal[pass],TW,TH,0,formats[pass],GL_UNSIGNED_BYTE,upload);
  legacy_readback_kind=pass<3?pass+1:0;
  check_case(names[pass],0);
  legacy_readback_kind=0;
 }
}
#define RUN_FULL(...) do { full_case(__VA_ARGS__);if(damaged_readback)return 0; } while(0)
static int run_cases(void)
{
 RUN_FULL("2d-rgba",GL_TEXTURE_2D,0,0,0,0,0,0,1);
 if(!rectangle_supported){puts("SKIP rectangle cases: unsupported");skips+=12;return 0;}
 RUN_FULL("rect-rgba",GL_TEXTURE_RECTANGLE_ARB,1,0,0,0,0,0,0);
 RUN_FULL("rect-bgra-rev",GL_TEXTURE_RECTANGLE_ARB,2,1,0,0,0,0,1);
 RUN_FULL("rect-padded-rgba",GL_TEXTURE_RECTANGLE_ARB,3,0,1,0,0,0,0);
 RUN_FULL("rect-padded-bgra-rev",GL_TEXTURE_RECTANGLE_ARB,4,1,1,0,0,0,0);
 if(pbo_supported)RUN_FULL("rect-pbo-padded",GL_TEXTURE_RECTANGLE_ARB,5,0,1,1,0,0,0);
 else {puts("SKIP PBO case: unsupported/setup failed");skips++;}
 RUN_FULL("rect-premult-blend",GL_TEXTURE_RECTANGLE_ARB,6,0,0,0,0,1,0);
 if(rowbytes_supported){
  RUN_FULL("rect-apple-rowbytes",GL_TEXTURE_RECTANGLE_ARB,7,0,1,0,1,0,0);
  select_texture(GL_TEXTURE_RECTANGLE_ARB);reset_unpack();fill_upload(8,TW,0,0,0,0);fill_expected(8);
  glPushClientAttrib(GL_CLIENT_PIXEL_STORE_BIT);glPixelStorei(ROW_BYTES_APPLE,UPLOAD_ROW*4);glPopClientAttrib();
  GLint restored=-1;glGetIntegerv(ROW_BYTES_APPLE,&restored);printf("client-stack restored_row_bytes=%d expected=0\n",restored);
  if(restored!=0){pending_case_errors++;glPixelStorei(ROW_BYTES_APPLE,0);}
  glTexSubImage2D(GL_TEXTURE_RECTANGLE_ARB,0,0,0,TW,TH,GL_RGBA,GL_UNSIGNED_BYTE,upload);check_case("rect-client-stack",0);if(damaged_readback)return 0;
 }else{puts("SKIP APPLE row-byte/stack cases: unsupported");skips+=2;}
 /* Reused atlas with partial updates, padded rows and skips; unaffected texels must survive. */
 select_texture(GL_TEXTURE_RECTANGLE_ARB);reset_unpack();fill_expected(0);fill_upload(0,TW,0,0,0,0);
 glTexSubImage2D(GL_TEXTURE_RECTANGLE_ARB,0,0,0,TW,TH,GL_RGBA,GL_UNSIGNED_BYTE,upload);
 unsigned patch_x=TW>64?TW/2-11:11,patch_y=TH>32?TH/2-5:5;
 for(unsigned phase=9;phase<13;phase++){
  char name[64];fill_upload(phase,UPLOAD_ROW,3,2,0,0);
  glPixelStorei(GL_UNPACK_ROW_LENGTH,UPLOAD_ROW);glPixelStorei(GL_UNPACK_SKIP_PIXELS,3);glPixelStorei(GL_UNPACK_SKIP_ROWS,2);
  glTexSubImage2D(GL_TEXTURE_RECTANGLE_ARB,0,patch_x,patch_y,23,9,GL_RGBA,GL_UNSIGNED_BYTE,upload);
  for(unsigned y=0;y<9;y++)for(unsigned x=0;x<23;x++)pixel_source(x,y,phase,expected+((y+patch_y)*TW+x+patch_x)*4);
  snprintf(name,sizeof(name),"rect-partial-%u",phase);reset_unpack();check_case(name,phase&1);if(damaged_readback)return 0;
 }
 return 0;
}
static void init_texture(GLenum target,GLuint name)
{
 glBindTexture(target,name);glTexParameteri(target,GL_TEXTURE_MIN_FILTER,GL_NEAREST);glTexParameteri(target,GL_TEXTURE_MAG_FILTER,GL_NEAREST);
 glTexParameteri(target,GL_TEXTURE_WRAP_S,GL_CLAMP_TO_EDGE);glTexParameteri(target,GL_TEXTURE_WRAP_T,GL_CLAMP_TO_EDGE);
 glTexImage2D(target,0,GL_RGBA8,TW,TH,0,GL_RGBA,GL_UNSIGNED_BYTE,NULL);
}

#include "masked-render-cases.h"
#include "packed-upload-cases.h"
int main(int argc,char **argv)
{
 setbuf(stdout,NULL);
 if((argc!=3 && !(argc==4&&(!strcmp(argv[3],"--packed-only")||!strcmp(argv[3],"--matrix-only")||!strcmp(argv[3],"--glyph-batch")||!strcmp(argv[3],"--glyph-program")))) || (strcmp(argv[1],"gpu")&&strcmp(argv[1],"software"))){fprintf(stderr,"usage: pixel-render-probe gpu|software NEW_OUTPUT_DIRECTORY [--packed-only|--matrix-only|--glyph-batch|--glyph-program]\n");return 2;}
 int gpu=!strcmp(argv[1],"gpu");output=argv[2];
 if(mkdir(output,0755)){perror("Use a NEW output directory");return 2;}
 printf("Offscreen reference probe v2; no test window, driver/config changes or sleep requests\n");
 printf("dimensions texture=%ux%u render=%ux%u padded_row_bytes=%u\n",TW,TH,W,H,UPLOAD_ROW*4);
 CGLPixelFormatAttribute attrs[8];unsigned a=0;
 attrs[a++]=kCGLPFARendererID;attrs[a++]=(CGLPixelFormatAttribute)(gpu?0x21a00:kCGLRendererGenericFloatID);
 if(gpu){attrs[a++]=kCGLPFAAccelerated;attrs[a++]=kCGLPFANoRecovery;}attrs[a]=0;
 CGLPixelFormatObj pf=NULL;CGLContextObj ctx=NULL;GLint n=0;
 CGLError e=CGLChoosePixelFormat(attrs,&pf,&n);
 if(e||!pf||!n){printf("SETUP_FAIL choose error=%d count=%d\n",e,n);return 2;}
 GLint id=0,accelerated=-1;CGLDescribePixelFormat(pf,0,kCGLPFARendererID,&id);CGLDescribePixelFormat(pf,0,kCGLPFAAccelerated,&accelerated);
 printf("requested=%s chosen_renderer=0x%x accelerated=%d\n",argv[1],id,accelerated);
 if(((unsigned)id&0x00ffff00u)!=(gpu?0x21a00u:(unsigned)kCGLRendererGenericFloatID) || (gpu&&accelerated!=1)||(!gpu&&accelerated!=0)){puts("SETUP_FAIL unexpected acceleration");CGLDestroyPixelFormat(pf);return 2;}
 e=CGLCreateContext(pf,NULL,&ctx);CGLDestroyPixelFormat(pf);
 if(e||!ctx){printf("SETUP_FAIL create error=%d\n",e);return 2;}
 e=CGLSetCurrentContext(ctx);if(e){printf("SETUP_FAIL current error=%d\n",e);CGLDestroyContext(ctx);return 2;}
 const GLubyte *vendor=glGetString(GL_VENDOR),*renderer=glGetString(GL_RENDERER),*version=glGetString(GL_VERSION);
 if(!vendor||!renderer||!version){puts("SETUP_FAIL missing GL identity strings");CGLSetCurrentContext(NULL);CGLDestroyContext(ctx);return 2;}
 printf("GL_VENDOR=%s\nGL_RENDERER=%s\nGL_VERSION=%s\n",vendor,renderer,version);
 if((gpu&&!strstr((const char*)renderer,"V7900")) ||
    (!gpu&&(!strstr((const char*)renderer,"Apple")||!strstr((const char*)renderer,"Software")))) {
  puts("SETUP_FAIL renderer identity does not match the requested comparison");CGLSetCurrentContext(NULL);CGLDestroyContext(ctx);return 2;
 }
 GLenum startup_error=glGetError();if(startup_error)printf("context startup GL_ERROR=0x%x\n",startup_error);
 GLint initial_pbo=0;glGetIntegerv(GL_PIXEL_UNPACK_BUFFER_BINDING,&initial_pbo);pbo_supported=glGetError()==GL_NO_ERROR;
 printf("PBO binding query=%s\n",pbo_supported?"accepted":"unsupported");
 glPixelStorei(ROW_BYTES_APPLE,0);GLenum row_error=glGetError();rowbytes_supported=row_error==GL_NO_ERROR;printf("APPLE_row_bytes setter=%s error=0x%x\n",rowbytes_supported?"accepted":"unsupported/error",row_error);
 glGenTextures(3,textures);init_texture(GL_TEXTURE_2D,textures[0]);init_texture(GL_TEXTURE_2D,textures[2]);
 glGenFramebuffersEXT(1,&fbo);glBindFramebufferEXT(GL_FRAMEBUFFER_EXT,fbo);
 glFramebufferTexture2DEXT(GL_FRAMEBUFFER_EXT,GL_COLOR_ATTACHMENT0_EXT,GL_TEXTURE_2D,textures[2],0);
 GLenum status=glCheckFramebufferStatusEXT(GL_FRAMEBUFFER_EXT);GLenum error=glGetError();
 if(status!=GL_FRAMEBUFFER_COMPLETE_EXT||error){printf("SETUP_FAIL framebuffer status=0x%x error=0x%x\n",status,error);goto cleanup;}
 glDrawBuffer(GL_COLOR_ATTACHMENT0_EXT);glReadBuffer(GL_COLOR_ATTACHMENT0_EXT);
 init_texture(GL_TEXTURE_RECTANGLE_ARB,textures[1]);GLenum rectangle_error=glGetError();rectangle_supported=rectangle_error==GL_NO_ERROR;
 printf("rectangle_texture=%s error=0x%x\n",rectangle_supported?"accepted":"unsupported/error",rectangle_error);
 if(gpu&&!rectangle_supported){puts("SETUP_FAIL GPU rectangle texture unavailable");goto cleanup;}
 if(pbo_supported){glGenBuffers(1,&pbo);GLenum error=glGetError();if(!pbo||error){printf("PBO allocation unavailable error=0x%x\n",error);pbo_supported=0;}}
 if(argc==4&&!strcmp(argv[3],"--glyph-program"))glyph_program_cases();
 else if(argc==4&&!strcmp(argv[3],"--glyph-batch"))glyph_batch_cases();
 else if(argc==4&&!strcmp(argv[3],"--matrix-only"))matrix_cases();
 else if(argc==4)packed_cases();
 else {
  run_cases();
  if(!damaged_readback)glyph_formats();
  if(rectangle_supported&&!damaged_readback)masked_cases();
 }
 printf("SUMMARY cases=%u failed=%u skipped_optional=%u\n",tests,failures,skips);
cleanup:
 if(pbo_supported){glBindBuffer(GL_PIXEL_UNPACK_BUFFER,0);glBindBuffer(GL_PIXEL_PACK_BUFFER,0);}
 if(pbo)glDeleteBuffers(1,&pbo);
 if(fbo)glDeleteFramebuffersEXT(1,&fbo);
 glDeleteTextures(3,textures);
 CGLSetCurrentContext(NULL);CGLDestroyContext(ctx);
 return !tests?2:failures?1:0;
}
