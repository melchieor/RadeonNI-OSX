/* Exact observed packed types plus format-order/byte-swap controls. MIT */
#include "packed-reference.h"
static void packed_fill(unsigned kind,unsigned phase,unsigned width,unsigned height,unsigned row_bytes,unsigned skip_x,unsigned skip_y,unsigned prefix,int swap)
{
 unsigned bpp=kind<2||kind==5?2:4;memset(upload,0xc7,sizeof(upload));
 for(unsigned y=0;y<height;y++)for(unsigned x=0;x<width;x++){
  unsigned char rgba[4];packed_source(kind,x,y,phase,rgba);
  packed_store(upload+prefix+(y+skip_y)*row_bytes+(x+skip_x)*bpp,packed_word(kind,rgba),bpp,swap);
 }
}
static int packed_transfer(unsigned kind,unsigned layout,GLenum target,GLenum format,GLenum type,unsigned phase,int sub,int sized)
{
 unsigned bpp=kind<2||kind==5?2:4;
 unsigned width=sub?(layout==1?3:layout==2?14:8):TW;
 unsigned height=sub?(layout==2?16:10):TH;
 unsigned row=width*bpp,sx=0,sy=0,prefix=layout==1?1:layout==3?64:0;
 if(layout==1)row=(width*bpp+3)&~3u;
 if(layout==2){row=(width+8)*bpp;sx=3;sy=2;}
 if(layout==3){row=width*bpp+17;sx=3;sy=2;}
 reset_unpack();packed_fill(kind,phase,width,height,row,sx,sy,prefix,layout==2);
 glPixelStorei(GL_UNPACK_ALIGNMENT,1);glPixelStorei(GL_UNPACK_SKIP_PIXELS,sx);glPixelStorei(GL_UNPACK_SKIP_ROWS,sy);
 if(layout==1||layout==3)glPixelStorei(ROW_BYTES_APPLE,row);
 else glPixelStorei(GL_UNPACK_ROW_LENGTH,row/bpp);
 if(layout==2)glPixelStorei(GL_UNPACK_SWAP_BYTES,GL_TRUE);
 const void *pointer=upload+prefix;
 if(layout==3){
  glBindBuffer(GL_PIXEL_UNPACK_BUFFER,pbo);glBufferData(GL_PIXEL_UNPACK_BUFFER,sizeof(upload),upload,GL_STREAM_DRAW);
  GLint binding=0;glGetIntegerv(GL_PIXEL_UNPACK_BUFFER_BINDING,&binding);GLenum e=glGetError();
  if(e||(GLuint)binding!=pbo){printf("PACKED_PBO_SETUP_FAIL error=%x binding=%u\n",e,(unsigned)binding);reset_unpack();return 0;}
  pointer=(void *)(uintptr_t)prefix;
 }
 if(sub){
  unsigned dx=TW-16,dy=5;
  glTexSubImage2D(target,0,dx,dy,width,height,format,type,pointer);
  for(unsigned y=0;y<height;y++)for(unsigned x=0;x<width;x++)packed_source(kind,x,y,phase,expected+((y+dy)*TW+x+dx)*4);
 }else{
  glTexImage2D(target,0,sized?GL_RGBA8:GL_RGBA,width,height,0,format,type,pointer);
  for(unsigned y=0;y<TH;y++)for(unsigned x=0;x<TW;x++)packed_source(kind,x,y,phase,expected+(y*TW+x)*4);
 }
 reset_unpack();return 1;
}
static void packed_cases(void)
{
 const char *kinds[]={"bgra1555rev","rgba1555rev","rgba8888","bgra8888","bgra8888rev","bgra4444rev"};
 const GLenum formats[]={GL_BGRA,GL_RGBA,GL_RGBA,GL_BGRA,GL_BGRA,GL_BGRA};
 const GLenum types[]={GL_UNSIGNED_SHORT_1_5_5_5_REV,GL_UNSIGNED_SHORT_1_5_5_5_REV,GL_UNSIGNED_INT_8_8_8_8,GL_UNSIGNED_INT_8_8_8_8,GL_UNSIGNED_INT_8_8_8_8_REV,GL_UNSIGNED_SHORT_4_4_4_4_REV};
 const char *layouts[]={"tight","apple-unaligned","swap-padded-skips","pbo-odd-byte-rows"};
 legacy_readback_kind=0;
 for(unsigned t=0;t<2&&!damaged_readback;t++){
  if(t&&!rectangle_supported){puts("SKIP packed rectangle cases");skips+=72;continue;}
  GLenum target=t?GL_TEXTURE_RECTANGLE_ARB:GL_TEXTURE_2D;select_texture(target);
  for(unsigned kind=0;kind<6&&!damaged_readback;kind++)for(unsigned layout=0;layout<4&&!damaged_readback;layout++){
   unsigned variants=kind<2||kind==5?2:1;
   if((layout==1||layout==3)&&!rowbytes_supported){printf("SKIP packed %s layout=%u: APPLE rows absent\n",kinds[kind],layout);skips+=2*variants;continue;}
   if(layout==3&&!pbo_supported){printf("SKIP packed %s: unpack PBO absent\n",kinds[kind]);skips+=2*variants;continue;}
   for(unsigned sized=0;sized<variants&&!damaged_readback;sized++)for(unsigned sub=0;sub<2&&!damaged_readback;sub++){
    char name[120];snprintf(name,sizeof(name),"packed-%s-%s-%s-sized%u-%s",kinds[kind],t?"rect":"2d",layouts[layout],sized,sub?"glyph-sub":"image");
    if(!packed_transfer(kind,layout,target,formats[kind],types[kind],kind*7+layout+sub*5,sub,sized)){
     printf("CASE %s FAIL setup\n",name);tests++;failures++;break;
    }
    check_case(name,0);
   }
  }
 }
}

/* Each row changes one setting from the tight CPU baseline, followed by
   combinations needed to reproduce the earlier ambiguous observations. */
static void matrix_cases(void)
{
 struct variant {const char *name; unsigned pad,sx,sy,swap,pbo,apple,odd,edge;} v[]={
  {"baseline",0,0,0,0,0,0,0,0},
  {"edge",0,0,0,0,0,0,0,1},
  {"padding",1,0,0,0,0,0,0,0},
  {"skip-pixels",1,3,0,0,0,0,0,0},
  {"skip-rows",0,0,2,0,0,0,0,0},
  {"byte-swap",0,0,0,1,0,0,0,0},
  {"pbo-aligned",0,0,0,0,1,0,0,0},
  {"apple-stride",1,0,0,0,0,1,0,0},
  {"pbo-odd-stride",1,0,0,0,1,1,1,0},
  {"padded-skips",1,3,2,0,0,0,0,0},
  {"swapped-padded-skips",1,3,2,1,0,0,0,0},
  {"edge-swapped-padded-skips",1,3,2,1,0,0,0,1},
  {"edge-padded-skips",1,3,2,0,0,0,0,1},
  {"pbo-odd-skips",1,3,2,0,1,1,1,0}
 };
 const unsigned kinds[]={0,2};
 for(unsigned t=0;t<2&&!damaged_readback;t++){
  if(t&&!rectangle_supported){puts("SKIP matrix rectangle unsupported");skips+=28;continue;}
  GLenum target=t?GL_TEXTURE_RECTANGLE_ARB:GL_TEXTURE_2D;select_texture(target);
  for(unsigned k=0;k<2&&!damaged_readback;k++)for(unsigned j=0;j<sizeof(v)/sizeof(v[0])&&!damaged_readback;j++){
   unsigned kind=kinds[k], bpp=kind==0?2:4, width=14,height=16;
   unsigned row=(width+(v[j].pad?8:0))*bpp+(v[j].odd?1:0);
   unsigned dx=v[j].edge?TW-16:100,dy=5,phase=23;
   GLenum fmt=kind==0?GL_BGRA:GL_RGBA,type=kind==0?GL_UNSIGNED_SHORT_1_5_5_5_REV:GL_UNSIGNED_INT_8_8_8_8;
   char name[128];snprintf(name,sizeof(name),"matrix-%s-%s-%s",kind==0?"bgra1555rev":"rgba8888",t?"rect":"2d",v[j].name);
   if((v[j].pbo&&!pbo_supported)||(v[j].apple&&!rowbytes_supported)){printf("CASE %s SKIP unsupported\n",name);skips++;continue;}
   /* Independent baseline: every variant starts with a newly defined image. */
   reset_unpack();packed_fill(kind,0,TW,TH,TW*bpp,0,0,0,0);
   glTexImage2D(target,0,GL_RGBA,TW,TH,0,fmt,type,upload);
   for(unsigned y=0;y<TH;y++)for(unsigned x=0;x<TW;x++)packed_source(kind,x,y,0,expected+(y*TW+x)*4);
   GLenum e=glGetError();if(e){printf("%s BASELINE_GL_ERROR=0x%x\n",name,e);pending_case_errors++;}
   unsigned prefix=v[j].pbo?64:0;
   packed_fill(kind,phase,width,height,row,v[j].sx,v[j].sy,prefix,v[j].swap);
   reset_unpack();glPixelStorei(GL_UNPACK_ALIGNMENT,1);
   glPixelStorei(GL_UNPACK_SKIP_PIXELS,v[j].sx);glPixelStorei(GL_UNPACK_SKIP_ROWS,v[j].sy);
   if(v[j].apple)glPixelStorei(ROW_BYTES_APPLE,row);else glPixelStorei(GL_UNPACK_ROW_LENGTH,row/bpp);
   if(v[j].swap)glPixelStorei(GL_UNPACK_SWAP_BYTES,GL_TRUE);
   const void *ptr=upload+prefix;
   if(v[j].pbo){GLint binding=0;glBindBuffer(GL_PIXEL_UNPACK_BUFFER,pbo);glBufferData(GL_PIXEL_UNPACK_BUFFER,sizeof(upload),upload,GL_STREAM_DRAW);glGetIntegerv(GL_PIXEL_UNPACK_BUFFER_BINDING,&binding);if((GLuint)binding!=pbo){printf("%s PBO_BINDING_MISMATCH=%d\n",name,binding);pending_case_errors++;}ptr=(void *)(uintptr_t)prefix;}
   e=glGetError();if(e){printf("%s SETUP_GL_ERROR=0x%x\n",name,e);pending_case_errors++;}
   glTexSubImage2D(target,0,dx,dy,width,height,fmt,type,ptr);
   e=glGetError();if(e){printf("%s UPLOAD_GL_ERROR=0x%x\n",name,e);pending_case_errors++;}
   for(unsigned y=0;y<height;y++)for(unsigned x=0;x<width;x++)packed_source(kind,x,y,phase,expected+((y+dy)*TW+x+dx)*4);
   reset_unpack();check_case(name,0);
  }
 }
}

/* Reused client-memory glyph atlas, repeated upload then vertex-array draw.
   Every source buffer is overwritten on the next upload; only the final
   framebuffer is read. This checks queued ordering and client buffer lifetime. */
static void glyph_batch_cases(void)
{
 if(!rectangle_supported||!rowbytes_supported){puts("SKIP glyph batches: rectangle or APPLE row bytes unavailable");skips+=16;return;}
 select_texture(GL_TEXTURE_RECTANGLE_ARB);reset_unpack();
 glViewport(0,0,W,H);glDisable(GL_DITHER);glDisable(GL_SCISSOR_TEST);glDisable(GL_DEPTH_TEST);glDisable(GL_STENCIL_TEST);glDisable(GL_ALPHA_TEST);
 glColorMask(GL_TRUE,GL_TRUE,GL_TRUE,GL_TRUE);glMatrixMode(GL_PROJECTION);glLoadIdentity();glOrtho(0,W,0,H,-1,1);glMatrixMode(GL_MODELVIEW);glLoadIdentity();glTexEnvi(GL_TEXTURE_ENV,GL_TEXTURE_ENV_MODE,GL_REPLACE);
 glEnableClientState(GL_VERTEX_ARRAY);glEnableClientState(GL_TEXTURE_COORD_ARRAY);
 const unsigned widths[]={3,7,8,9};
 for(unsigned small=0;small<4&&!damaged_readback;small++)for(unsigned blend=0;blend<2&&!damaged_readback;blend++)for(unsigned large=0;large<2&&!damaged_readback;large++){
  unsigned width=widths[small],height=10,count=large?128:32,row=(width*2+3)&~3u;
  char name[80],path[128];snprintf(name,sizeof(name),"glyph-batch-w%u-%s-n%u",width,blend?"blend":"replace",count);
  reset_unpack();memset(upload,0,sizeof(upload));glTexImage2D(GL_TEXTURE_RECTANGLE_ARB,0,GL_RGBA8,TW,TH,0,GL_BGRA,GL_UNSIGNED_SHORT_1_5_5_5_REV,upload);
  if(blend){glEnable(GL_BLEND);glBlendFunc(GL_ONE,GL_ONE_MINUS_SRC_ALPHA);}else glDisable(GL_BLEND);
  glClearColor(37.0f/255,71.0f/255,109.0f/255,1);glClear(GL_COLOR_BUFFER_BIT);
  for(unsigned i=0;i<W*H;i++){reference[i*4]=37;reference[i*4+1]=71;reference[i*4+2]=109;reference[i*4+3]=255;}
  for(unsigned n=0;n<count;n++){
   unsigned dx=(n%16)*12,dy=(n/16)*12,ax=(n&1)?16:0,phase=11+n;
   packed_fill(0,phase,width,height,row,0,0,0,0);glPixelStorei(ROW_BYTES_APPLE,row);
   glTexSubImage2D(GL_TEXTURE_RECTANGLE_ARB,0,ax,0,width,height,GL_BGRA,GL_UNSIGNED_SHORT_1_5_5_5_REV,upload);
   GLfloat vertices[8]={dx,dy,dx+width,dy,dx+width,dy+height,dx,dy+height};
   GLfloat coords[8]={ax,0,ax+width,0,ax+width,height,ax,height};
   glVertexPointer(2,GL_FLOAT,0,vertices);glTexCoordPointer(2,GL_FLOAT,0,coords);glDrawArrays(GL_QUADS,0,4);
   for(unsigned y=0;y<height;y++)for(unsigned x=0;x<width;x++){
    unsigned char src[4],*dst=reference+((dy+y)*W+dx+x)*4;packed_source(0,x,y,phase,src);
    if(!blend)memcpy(dst,src,4);else {for(unsigned k=0;k<3;k++){unsigned v=src[k]+(dst[k]*(255u-src[3])+127)/255;dst[k]=v>255?255:v;}dst[3]=255;}
   }
  }
  reset_unpack();memset(rendered,0xcd,sizeof(rendered));glReadPixels(0,0,W,H,GL_RGBA,GL_UNSIGNED_BYTE,rendered);
  unsigned bad=compare(name,"render",reference,rendered,W*H,W);
  for(unsigned i=W*H*4;i<sizeof(rendered);i++)if(rendered[i]!=0xcd){printf("%s GUARD_DAMAGE byte=%u\n",name,i);bad++;damaged_readback=1;break;}
  for(unsigned n=0;n<8;n++){GLenum e=glGetError();if(!e)break;printf("%s GL_ERROR=0x%x\n",name,e);bad++;}
  snprintf(path,sizeof(path),"%s-expected",name);if(!ppm(path,reference,W,H))bad++;
  snprintf(path,sizeof(path),"%s-rendered",name);if(!ppm(path,rendered,W,H))bad++;
  tests++;if(bad)failures++;printf("CASE %s %s\n",name,bad?"FAIL":"PASS");
 }
 glDisableClientState(GL_VERTEX_ARRAY);glDisableClientState(GL_TEXTURE_COORD_ARRAY);glDisable(GL_BLEND);
}

/* Synthetic fragment arithmetic informed by the trace, not app shader code.
   Independent CPU expectation; tests modulation, clipping and blending. */
static void glyph_program_cases(void)
{
 if(!rectangle_supported){puts("SKIP shader cases: rectangle unavailable");skips+=12;return;}
 static const char source[]="!!ARBfp1.0\nTEMP v,s,c;\nKIL fragment.texcoord[3];\nMOV_SAT v, fragment.texcoord[3];\nMUL c.x, v.x, v.y;\nMUL c.x, c.x, v.z;\nMUL c.x, c.x, v.w;\nTEX s, fragment.texcoord[0], texture[0], RECT;\nMUL s, s, fragment.color;\nMUL result.color, s, c.x;\nEND\n";
 GLuint program=0;glGenProgramsARB(1,&program);glBindProgramARB(GL_FRAGMENT_PROGRAM_ARB,program);
 glProgramStringARB(GL_FRAGMENT_PROGRAM_ARB,GL_PROGRAM_FORMAT_ASCII_ARB,(GLsizei)strlen(source),source);
 GLint position=0;glGetIntegerv(GL_PROGRAM_ERROR_POSITION_ARB,&position);GLenum err=glGetError();
 if(!program||position!=-1||err){printf("SETUP_FAIL program position=%d error=0x%x\n",position,err);tests++;failures++;if(program)glDeleteProgramsARB(1,&program);return;}
 select_texture(GL_TEXTURE_RECTANGLE_ARB);reset_unpack();glEnable(GL_FRAGMENT_PROGRAM_ARB);
 glViewport(0,0,W,H);glDisable(GL_DITHER);glDisable(GL_SCISSOR_TEST);glDisable(GL_DEPTH_TEST);glDisable(GL_STENCIL_TEST);glDisable(GL_ALPHA_TEST);glColorMask(GL_TRUE,GL_TRUE,GL_TRUE,GL_TRUE);
 glMatrixMode(GL_PROJECTION);glLoadIdentity();glOrtho(0,W,0,H,-1,1);glMatrixMode(GL_MODELVIEW);glLoadIdentity();
 glEnableClientState(GL_VERTEX_ARRAY);glEnableClientState(GL_TEXTURE_COORD_ARRAY);
 GLfloat vertices[8]={0,0,W,0,W,H,0,H},coords[8]={0,0,W,0,W,H,0,H};
 glVertexPointer(2,GL_FLOAT,0,vertices);glTexCoordPointer(2,GL_FLOAT,0,coords);glColor4ub(60,110,166,204);
 for(unsigned kindidx=0;kindidx<2&&!damaged_readback;kindidx++)for(unsigned blend=0;blend<2&&!damaged_readback;blend++)for(unsigned coverage=0;coverage<3&&!damaged_readback;coverage++){
  unsigned kind=kindidx?2:0,bpp=kind?4:2;float factor=coverage==0?1:coverage==1?0.5f:0;
  GLenum fmt=kind?GL_RGBA:GL_BGRA,type=kind?GL_UNSIGNED_INT_8_8_8_8:GL_UNSIGNED_SHORT_1_5_5_5_REV;
  char name[80],path[128];snprintf(name,sizeof(name),"glyph-program-%s-%s-%s",kind?"rgba8888":"bgra1555",blend?"blend":"replace",coverage==0?"full":coverage==1?"half":"clip");
  packed_fill(kind,9,TW,TH,TW*bpp,0,0,0,0);reset_unpack();glTexImage2D(GL_TEXTURE_RECTANGLE_ARB,0,GL_RGBA8,TW,TH,0,fmt,type,upload);
  if(blend){glEnable(GL_BLEND);glBlendFunc(GL_ONE,GL_ONE_MINUS_SRC_ALPHA);}else glDisable(GL_BLEND);
  glClearColor(37.0f/255,71.0f/255,109.0f/255,1);glClear(GL_COLOR_BUFFER_BIT);
  glMultiTexCoord4f(GL_TEXTURE3,coverage==2?-1.0f:factor,1,1,1);glDrawArrays(GL_QUADS,0,4);
  for(unsigned y=0;y<H;y++)for(unsigned x=0;x<W;x++){
   unsigned char s[4],*out=reference+(y*W+x)*4;packed_source(kind,x,y,9,s);
   if(coverage==2){out[0]=37;out[1]=71;out[2]=109;out[3]=255;continue;}
   const float ink[4]={60,110,166,204},bg[4]={37,71,109,255};
   float alpha=(s[3]/255.0f)*(ink[3]/255.0f)*factor;
   for(unsigned k=0;k<4;k++){
    float v=(s[k]/255.0f)*(ink[k]/255.0f)*factor;
    if(blend)v+=(bg[k]/255.0f)*(1-alpha);
    int byte=(int)(v*255.0f+0.5f);out[k]=byte<0?0:byte>255?255:byte;
   }
  }
  memset(rendered,0xcd,sizeof(rendered));glReadPixels(0,0,W,H,GL_RGBA,GL_UNSIGNED_BYTE,rendered);
  unsigned bad=compare(name,"render",reference,rendered,W*H,W);
  for(unsigned i=W*H*4;i<sizeof(rendered);i++)if(rendered[i]!=0xcd){printf("%s GUARD_DAMAGE byte=%u\n",name,i);bad++;damaged_readback=1;break;}
  for(unsigned n=0;n<8;n++){GLenum e=glGetError();if(!e)break;printf("%s GL_ERROR=0x%x\n",name,e);bad++;}
  snprintf(path,sizeof(path),"%s-expected",name);if(!ppm(path,reference,W,H))bad++;
  snprintf(path,sizeof(path),"%s-rendered",name);if(!ppm(path,rendered,W,H))bad++;
  tests++;if(bad)failures++;printf("CASE %s %s\n",name,bad?"FAIL":"PASS");
 }
 glDisableClientState(GL_VERTEX_ARRAY);glDisableClientState(GL_TEXTURE_COORD_ARRAY);glDisable(GL_FRAGMENT_PROGRAM_ARB);glDisable(GL_BLEND);glDeleteProgramsARB(1,&program);
}
