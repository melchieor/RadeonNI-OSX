/* Fresh synthetic ARB programs; not copied from captured application shaders.
   Exercises independent mask/destination sampling, channel masks, gamma-like
   arithmetic, KIL clipping and repeated uploads. MIT, kouta-kun and Claude. */
#include "masked-reference.h"
static void masked_cases(void)
{
 const GLenum format[]={GL_ALPHA,GL_LUMINANCE,GL_LUMINANCE_ALPHA,GL_RGB,GL_RGBA};
 const GLint internal[]={GL_ALPHA8,GL_LUMINANCE8,GL_LUMINANCE8_ALPHA8,GL_RGB8,GL_RGBA8};
 const unsigned components[]={1,1,2,3,4};
 const char *label[]={"a","l","la","rgb","rgba"};
 const char *programs[]={
 "!!ARBfp1.0\nPARAM ink=program.local[0]; TEMP mask,base; KIL fragment.texcoord[3]; TEX mask,fragment.texcoord[0],texture[0],RECT; TEX base,fragment.texcoord[1],texture[1],RECT; LRP result.color,mask.g,ink,base; END\n",
 "!!ARBfp1.0\nPARAM ink=program.local[0]; TEMP mask,base; KIL fragment.texcoord[3]; TEX mask,fragment.texcoord[0],texture[0],RECT; TEX base,fragment.texcoord[1],texture[1],RECT; MUL mask.g,mask.g,mask.g; LRP result.color,mask.g,ink,base; END\n",
 "!!ARBfp1.0\nPARAM ink=program.local[0]; TEMP mask,base,color,power; KIL fragment.texcoord[3]; TEX mask,fragment.texcoord[0],texture[0],RECT; TEX base,fragment.texcoord[1],texture[1],RECT; MUL mask.rgb,mask,mask; MUL base.rgb,base,base; MUL color.rgb,ink,ink; LRP color.rgb,mask,color,base; MAX power.rgb,color,0.000001; RSQ power.r,power.r; RSQ power.g,power.g; RSQ power.b,power.b; MUL result.color.rgb,color,power; MOV result.color.a,1.0; END\n"};
 GLuint mask=0,background=0,program=0;
 glGenTextures(1,&mask);glGenTextures(1,&background);glGenProgramsARB(1,&program);
 if(!mask||!background||!program){puts("SETUP_FAIL masked object creation");tests++;failures++;return;}
 reset_unpack();
 for(unsigned unit=0;unit<2;unit++){
  glActiveTexture(GL_TEXTURE0+unit);glDisable(GL_TEXTURE_2D);glDisable(GL_TEXTURE_RECTANGLE_ARB);
  glBindTexture(GL_TEXTURE_RECTANGLE_ARB,unit?background:mask);
  glTexParameteri(GL_TEXTURE_RECTANGLE_ARB,GL_TEXTURE_MIN_FILTER,GL_NEAREST);glTexParameteri(GL_TEXTURE_RECTANGLE_ARB,GL_TEXTURE_MAG_FILTER,GL_NEAREST);
  glTexParameteri(GL_TEXTURE_RECTANGLE_ARB,GL_TEXTURE_WRAP_S,GL_CLAMP_TO_EDGE);glTexParameteri(GL_TEXTURE_RECTANGLE_ARB,GL_TEXTURE_WRAP_T,GL_CLAMP_TO_EDGE);
 }
 for(unsigned y=0;y<TH;y++)for(unsigned x=0;x<TW;x++)mask_destination(x,y,upload+(y*TW+x)*4);
 glTexImage2D(GL_TEXTURE_RECTANGLE_ARB,0,GL_RGBA8,TW,TH,0,GL_RGBA,GL_UNSIGNED_BYTE,upload);
 glActiveTexture(GL_TEXTURE0);glBindProgramARB(GL_FRAGMENT_PROGRAM_ARB,program);
 glEnable(GL_FRAGMENT_PROGRAM_ARB);glProgramLocalParameter4fARB(GL_FRAGMENT_PROGRAM_ARB,0,128.0f/255,64.0f/255,192.0f/255,1);
 glDisable(GL_BLEND);glDisable(GL_DITHER);glDisable(GL_SCISSOR_TEST);glDisable(GL_DEPTH_TEST);glDisable(GL_STENCIL_TEST);glDisable(GL_ALPHA_TEST);
 glColorMask(GL_TRUE,GL_TRUE,GL_TRUE,GL_TRUE);glViewport(0,0,W,H);
 glMatrixMode(GL_PROJECTION);glLoadIdentity();glOrtho(0,W,0,H,-1,1);glMatrixMode(GL_MODELVIEW);glLoadIdentity();
 for(unsigned f=0;f<5 && !damaged_readback;f++){
  glTexImage2D(GL_TEXTURE_RECTANGLE_ARB,0,internal[f],TW,TH,0,format[f],GL_UNSIGNED_BYTE,NULL);
  for(unsigned p=0;p<3 && !damaged_readback;p++){
   glProgramStringARB(GL_FRAGMENT_PROGRAM_ARB,GL_PROGRAM_FORMAT_ASCII_ARB,(GLsizei)strlen(programs[p]),programs[p]);
   GLint position=0;glGetIntegerv(GL_PROGRAM_ERROR_POSITION_ARB,&position);GLenum compile_error=glGetError();
   if(position!=-1||compile_error){printf("masked format=%s program=%u COMPILE_FAIL position=%d error=0x%x\n",label[f],p,position,compile_error);tests++;failures++;continue;}
   for(unsigned clip=0;clip<2 && !damaged_readback;clip++){
    char name[80],path[120];snprintf(name,sizeof(name),"masked-%s-p%u-clip%u",label[f],p,clip);unsigned phase=f*6+p*2+clip;
    for(unsigned y=0;y<TH;y++)for(unsigned x=0;x<TW;x++){
     unsigned char m[4];mask_input(x,y,phase,f,m);unsigned char *d=upload+(y*TW+x)*components[f];
     if(f==0)d[0]=m[3];else if(f==2){d[0]=m[0];d[1]=m[3];}else memcpy(d,m,components[f]);
    }
    glTexSubImage2D(GL_TEXTURE_RECTANGLE_ARB,0,0,0,TW,TH,format[f],GL_UNSIGNED_BYTE,upload);
    glClearColor(37.0f/255,71.0f/255,109.0f/255,1);glClear(GL_COLOR_BUFFER_BIT);
    glBegin(GL_QUADS);
    for(unsigned vertex=0;vertex<4;vertex++){
     unsigned x=vertex==1||vertex==2?W:0,y=vertex>=2?H:0;
     glMultiTexCoord2f(GL_TEXTURE0,x,y);glMultiTexCoord2f(GL_TEXTURE1,x,y);
     glMultiTexCoord4f(GL_TEXTURE3,clip?((float)x-(W/3))/W:1,1,1,1);glVertex2f(x,y);
    }
    glEnd();
    for(unsigned y=0;y<H;y++)for(unsigned x=0;x<W;x++){
     unsigned char *d=reference+(y*W+x)*4,m[4],b[4];
     if(clip&&x<W/3){d[0]=37;d[1]=71;d[2]=109;d[3]=255;}
     else {mask_input(x,y,phase,f,m);mask_destination(x,y,b);mask_composite(m,b,p,d);}
    }
    memset(rendered,0xcd,sizeof(rendered));glReadPixels(0,0,W,H,GL_RGBA,GL_UNSIGNED_BYTE,rendered);
    unsigned bad=compare(name,"render",reference,rendered,W*H,W);
    for(unsigned i=W*H*4;i<sizeof(rendered);i++)if(rendered[i]!=0xcd){printf("%s GUARD_DAMAGE byte=%u\n",name,i);bad++;damaged_readback=1;break;}
    for(unsigned n=0;n<8;n++){GLenum e=glGetError();if(!e)break;printf("%s GL_ERROR=0x%x\n",name,e);bad++;}
    snprintf(path,sizeof(path),"%s-expected",name);if(!ppm(path,reference,W,H))bad++;
    snprintf(path,sizeof(path),"%s-rendered",name);if(!ppm(path,rendered,W,H))bad++;
    tests++;if(bad)failures++;printf("CASE %s %s\n",name,bad?"FAIL":"PASS");
   }
  }
 }
 glDisable(GL_FRAGMENT_PROGRAM_ARB);glDeleteProgramsARB(1,&program);
 glActiveTexture(GL_TEXTURE1);glBindTexture(GL_TEXTURE_RECTANGLE_ARB,0);glActiveTexture(GL_TEXTURE0);
 glDeleteTextures(1,&mask);glDeleteTextures(1,&background);
}
