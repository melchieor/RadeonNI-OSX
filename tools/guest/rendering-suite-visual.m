/* Own-window Cocoa/GL redraw exercise. MIT, kouta-kun and Claude. */
#import <Cocoa/Cocoa.h>
#import <OpenGL/gl.h>
#include <stdio.h>
#include <time.h>
#include <string.h>
static unsigned gpu_draws,other_draws;
@interface SuiteGLView : NSOpenGLView
@end
@implementation SuiteGLView
- (void)drawRect:(NSRect)rect
{
 (void)rect;[[self openGLContext] makeCurrentContext];
 const char *renderer=(const char *)glGetString(GL_RENDERER);
 if(renderer&&strstr(renderer,"V7900"))gpu_draws++;else other_draws++;
 if(gpu_draws+other_draws<=3)printf("DRAW_RENDERER=%s GPU_draws=%u other_draws=%u\n",renderer?renderer:"(null)",gpu_draws,other_draws);
 NSRect b=[self bounds];glViewport(0,0,b.size.width,b.size.height);
 glDisable(GL_DITHER);glClearColor(0.1,0.2,0.3,1);glClear(GL_COLOR_BUFFER_BIT);
 glBegin(GL_QUADS);
 glColor3f(1,0,0);glVertex2f(-0.9,-0.9);glVertex2f(-0.1,-0.9);glVertex2f(-0.1,0.9);glVertex2f(-0.9,0.9);
 glColor3f(0,1,0);glVertex2f(0.1,-0.9);glVertex2f(0.9,-0.9);glVertex2f(0.9,0.9);glVertex2f(0.1,0.9);
 glEnd();[[self openGLContext] flushBuffer];
}
@end
int main(void)
{
 setbuf(stdout,NULL);NSAutoreleasePool *pool=[[NSAutoreleasePool alloc] init];
 [NSApplication sharedApplication];
 NSWindow *text=[[NSWindow alloc] initWithContentRect:NSMakeRect(100,180,620,280)
  styleMask:NSTitledWindowMask|NSClosableWindowMask|NSResizableWindowMask backing:NSBackingStoreBuffered defer:NO];
 [text setReleasedWhenClosed:NO];[text setTitle:@"RadeonNI visual check: text / selection / popup / redraw"];
 NSTextField *label=[[NSTextField alloc] initWithFrame:NSMakeRect(20,200,580,48)];
 [label setStringValue:@"Look for missing letters, wallpaper holes or stale pixels.\nThis window and the GL window will move and resize for 25 seconds."];
 [label setEditable:NO];[label setBordered:NO];[label setDrawsBackground:NO];[[text contentView] addSubview:label];
 NSTextField *field=[[NSTextField alloc] initWithFrame:NSMakeRect(20,145,560,28)];
 [field setStringValue:@"Rename test: iii WWW New Folder Built-in Audio 0123456789"];
 [[text contentView] addSubview:field];
 NSPopUpButton *popup=[[NSPopUpButton alloc] initWithFrame:NSMakeRect(20,85,350,32) pullsDown:NO];
 [popup addItemsWithTitles:[NSArray arrayWithObjects:@"Open this popup and check its text",@"New Folder",@"Built-in Audio",@"Selection and transparency",nil]];
 [[text contentView] addSubview:popup];
 NSWindow *glwin=[[NSWindow alloc] initWithContentRect:NSMakeRect(500,100,360,230)
  styleMask:NSTitledWindowMask|NSClosableWindowMask|NSResizableWindowMask backing:NSBackingStoreBuffered defer:NO];
 [glwin setReleasedWhenClosed:NO];[glwin setTitle:@"GL: solid red left / green right"];
 NSOpenGLPixelFormatAttribute attrs[]={NSOpenGLPFAAccelerated,NSOpenGLPFANoRecovery,NSOpenGLPFARendererID,0x21a00,NSOpenGLPFADoubleBuffer,0};
 NSOpenGLPixelFormat *pf=[[NSOpenGLPixelFormat alloc] initWithAttributes:attrs];
 SuiteGLView *glview=pf?[[SuiteGLView alloc] initWithFrame:NSMakeRect(0,0,360,230) pixelFormat:pf]:nil;
 if(!glview||![glview openGLContext]){puts("SETUP_FAIL visual GL context");return 2;}
 [glview setAutoresizingMask:NSViewWidthSizable|NSViewHeightSizable];[glwin setContentView:glview];
 [[glview openGLContext] makeCurrentContext];
 const char *renderer=(const char *)glGetString(GL_RENDERER);printf("PRE_DRAW_RENDERER=%s (informational before window attachment)\n",renderer?renderer:"(null)");

 [glwin orderFront:nil];[text makeKeyAndOrderFront:nil];[field selectText:nil];[NSApp activateIgnoringOtherApps:YES];
 puts("VISUAL_ONLY: inspect selected text, open popup, watch occlusion/resize; no automatic compositor pass claim.");
 time_t start=time(NULL);unsigned step=0;
 while(time(NULL)-start<25){
  NSAutoreleasePool *frame=[[NSAutoreleasePool alloc] init];
  NSEvent *e=[NSApp nextEventMatchingMask:NSAnyEventMask untilDate:[NSDate dateWithTimeIntervalSinceNow:0.1] inMode:NSDefaultRunLoopMode dequeue:YES];
  if(e)[NSApp sendEvent:e];
  if(![text isVisible]||![glwin isVisible])break;
  if(++step%10==0){unsigned phase=(step/10)%4;
   [glwin setFrame:NSMakeRect(450+phase*25,120+phase*12,360+phase*13,230+phase*7) display:YES];
   [text setFrame:NSMakeRect(100+phase*7,180,620+phase*5,302) display:YES];
   [text display];[glview setNeedsDisplay:YES];
  }
  [NSApp updateWindows];[frame release];
 }
 [[glview openGLContext] makeCurrentContext];GLenum error=glGetError();
 printf("VISUAL_ONLY completed GL_error=0x%x GPU_draws=%u other_draws=%u; user observation required\n",error,gpu_draws,other_draws);
 if(!gpu_draws)puts("SETUP_FAIL no V7900 draw observed; this does not qualify accelerated presentation");
 [text close];[glwin close];[popup release];[field release];[label release];[glview release];[pf release];[text release];[glwin release];[pool release];
 return !gpu_draws?2:error?1:0;
}
