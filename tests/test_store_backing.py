"""Check the explicit CPU publication versus GPU-only store contract."""
import pathlib,subprocess,tempfile,unittest
ROOT=pathlib.Path(__file__).resolve().parents[1]
class StoreBackingTest(unittest.TestCase):
 def test_gpu_only_rebind_clears_publication_pointer(self):
  text=(ROOT/'mesa/frontend/osmesa.c').read_text();start=text.index('OSMesaStoreBacking(OSMesaContext');end=text.index('\n}',start)+2;body=text[start:end].replace('OSMesaStoreBacking(', 'int OSMesaStoreBacking(')
  prefix=r"""
#include <cassert>
#include <cstddef>
#include <cstdint>
using GLsizei=int;
#define GL_FALSE 0
#define GL_TRUE 1
#define PIPE_TEXTURE_RECT 1
#define PIPE_USAGE_DEFAULT 2
#define PIPE_BIND_RENDER_TARGET 4
#define WINSYS_HANDLE_TYPE_KMS 8
struct pipe_resource {unsigned target,format,width0,height0,depth0,array_size,usage,bind;};
struct winsys_handle {unsigned type,handle,stride;void *name;uintptr_t offset;uint64_t size;};
struct rdn_host_import {void *pages;void (*release)(void*);};
struct pipe_screen;
struct pipe_screen {pipe_resource *(*resource_from_handle)(pipe_screen*,pipe_resource*,winsys_handle*,unsigned);};
struct pipe_context {pipe_screen *screen;};
struct state_tracker {pipe_context *pipe;};
struct osmesa_buffer {bool store;unsigned width,height;struct{int color_format;}visual;void *map;int backing_stride;bool bottom_up;pipe_resource *backing_res;};
struct context{osmesa_buffer *current_buffer;state_tracker *st;};using OSMesaContext=context*;
static unsigned imports,releases;static bool fail_import;static pipe_resource gpu{};
void osmesa_sync(OSMesaContext){} int util_format_get_blocksize(int){return 4;}
void osmesa_backing_release(void*){}
void pipe_resource_reference(pipe_resource **resource,pipe_resource *value){if(*resource)++releases;*resource=value;}
pipe_resource *import_backing(pipe_screen*,pipe_resource *templ,winsys_handle *handle,unsigned){
 ++imports;auto host=(rdn_host_import*)handle->name;
 assert(templ->target==PIPE_TEXTURE_RECT && templ->bind==PIPE_BIND_RENDER_TARGET);
 assert(handle->type==WINSYS_HANDLE_TYPE_KMS && handle->handle==0x7572);
 assert(!handle->offset && !(handle->stride&255) && !(handle->size&4095));
 assert(host->pages && host->release==osmesa_backing_release);
 return fail_import?nullptr:&gpu;
}
"""
  suffix=r"""
int main(){int pixels;pipe_screen screen{import_backing};pipe_context pipe{&screen};state_tracker st{&pipe};
 osmesa_buffer b{};b.store=true;b.width=16;b.height=4;b.map=&pixels;b.backing_stride=128;
 context c{&b,&st};
 assert(OSMesaStoreBacking(&c,nullptr,0));assert(!b.map&&!b.backing_stride&&b.store);
 assert(!OSMesaStoreBacking(&c,nullptr,128)&&!b.map);
 assert(!OSMesaStoreBacking(&c,&pixels,63)&&!b.map);
 assert(OSMesaStoreBacking(&c,&pixels,64)&&b.map==&pixels&&b.backing_stride==64);
 assert(OSMesaStoreBacking(&c,nullptr,0)&&!b.map);
 alignas(4096) unsigned char aligned[4096];
 assert(OSMesaStoreBacking(&c,aligned,256)&&b.backing_res==&gpu&&imports==1);
 assert(OSMesaStoreBacking(&c,aligned,256)&&imports==1); // unchanged binding
 assert(OSMesaStoreBacking(&c,nullptr,0)&&!b.map&&!b.backing_res&&releases==1);
 fail_import=true;assert(OSMesaStoreBacking(&c,aligned,256)&&b.map==aligned&&!b.backing_res);
 b.store=false;assert(!OSMesaStoreBacking(&c,&pixels,64));assert(!OSMesaStoreBacking(nullptr,nullptr,0));}
"""
  with tempfile.TemporaryDirectory() as d:
   p=pathlib.Path(d);(p/'test.cpp').write_text(prefix+body+suffix);subprocess.run(['c++','-std=c++17',str(p/'test.cpp'),'-o',str(p/'test')],check=True);subprocess.run([str(p/'test')],check=True)
if __name__=='__main__':unittest.main()
