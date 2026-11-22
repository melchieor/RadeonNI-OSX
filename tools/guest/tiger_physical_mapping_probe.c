/* Private unique-mapping redirect test; never maps the framebuffer. MIT. */
#define check old_mapping_check
#define initrdn_mapping_probe old_mapping_module_init
#include "tiger_mapping_probe.c"
#undef check
#undef initrdn_mapping_probe

static void *unique_gate_thread(void *arg)
{
 struct gate_call *call=(struct gate_call *)arg;
 call->status=IOConnectMethodScalarIScalarO(call->connection,RDN_UC_SLEEP_MAPPING_PHYSICAL_PROBE,1,1,400,&call->outcome);
 return 0;
}
static int observe(io_service_t service,io_connect_t connection,volatile UInt32 *ptr,int writing)
{
 struct gate_call call;pthread_t thread;int seen=0,active_after;uint64_t begin,end;
 volatile UInt32 value=0;memset(&call,0,sizeof(call));call.connection=connection;
 if(active(service)||pthread_create(&thread,0,unique_gate_thread,&call))return -1;
 for(unsigned i=0;i<1500;i++){if(active(service)){seen=1;break;}usleep(1000);}
 if(!seen){fprintf(stderr,"Physical mapping redirect marker not seen; inconclusive.\n");pthread_join(thread,0);return -1;}
 begin=now_us();
 if(writing)*ptr=0x1468ace1u;else value=*ptr;
 end=now_us();active_after=active(service);
 if(pthread_join(thread,0))return -1;
 printf("PHYSICAL_%s_DELAY_US=%llu active_after=%d status=0x%x outcome=%u\n",
        writing?"WRITE":"READ",(unsigned long long)(end>=begin?end-begin:0),active_after,call.status,call.outcome);
 if(call.status||call.outcome!=3||!begin||end<begin||active(service))return -1;
 if(active_after){fprintf(stderr,"Physical mapping access completed while redirect marker was active.\n");return -1;}
 if(end-begin<50000||end-begin>3000000){fprintf(stderr,"Physical mapping timing inconclusive.\n");return -1;}
 if((writing&&*ptr!=0x1468ace1u)||(!writing&&value!=0x73ac19e5u))return -1;
 return 0;
}
static int address_mapped(vm_address_t address)
{
 vm_address_t region=address;vm_size_t size=0;mach_port_t object=MACH_PORT_NULL;
 struct vm_region_basic_info info;mach_msg_type_number_t count=VM_REGION_BASIC_INFO_COUNT;
 kern_return_t kr=vm_region(mach_task_self(),&region,&size,VM_REGION_BASIC_INFO,
                           (vm_region_info_t)&info,&count,&object);
 if(object!=MACH_PORT_NULL)mach_port_deallocate(mach_task_self(),object);
 if(kr==KERN_INVALID_ADDRESS)return 0;
 if(kr!=KERN_SUCCESS)return -1;
 return region<=address && address-region<size;
}
static PyObject *check(PyObject *self,PyObject *args)
{
 io_service_t service=0;io_connect_t connection=0;vm_address_t addr=0;vm_size_t len=0;
 int mapped=0,ok=0;kern_return_t e;
 (void)self;if(!PyArg_ParseTuple(args,""))return NULL;
 if(geteuid()!=0){PyErr_SetString(PyExc_RuntimeError,"Run as administrator");return NULL;}
 service=rdn_probe_device("6704");if(!service)goto done;
 if(IOServiceOpen(service,mach_task_self(),RDN_UC_TYPE_V2,&connection))goto done;
 e=IOConnectMapMemory(connection,RDN_UC_MEMORY_PHYSICAL_PROBE,mach_task_self(),&addr,&len,kIOMapAnywhere);
 if(e){fprintf(stderr,"Physical mapping failed 0x%x\n",e);goto done;}
 mapped=1;if(len<4096||address_mapped(addr)!=1)goto done;
 *(volatile UInt32 *)addr=0x73ac19e5u;
 if(observe(service,connection,(volatile UInt32 *)addr,0))goto done;
 if(observe(service,connection,(volatile UInt32 *)addr,1))goto done;
 puts("PHYSICAL_PRIVATE_MAPPING_PASS: reads and writes waited, then completed.");ok=1;
done:
 /* Tiger's standard unmap lookup cannot locate a kIOMapPhysical mapping.
  * Closing the owning client runs freeAll(), which unmaps its retained map.
  * Verify actual removal, not merely the close return code. */
 if(connection&&IOServiceClose(connection))ok=0;
 if(mapped){int remaining=address_mapped(addr);printf("PHYSICAL_ADDRESS_MAPPED_AFTER_CLOSE=%d\n",remaining);if(remaining!=0)ok=0;}
 if(service)IOObjectRelease(service);
 fflush(stdout);fflush(stderr);
 if(!ok){PyErr_SetString(PyExc_RuntimeError,"Physical mapping test failed or inconclusive");return NULL;}
 puts("PHYSICAL_PRIVATE_CLEANUP_PASS: client closed and VM region is absent.");fflush(stdout);
 Py_INCREF(Py_None);return Py_None;
}
static PyMethodDef unique_methods[]={{"check",check,METH_VARARGS,"Test an isolated physical mapping."},{0,0,0,0}};
PyMODINIT_FUNC initrdn_physical_mapping_probe(void){Py_InitModule("rdn_physical_mapping_probe",unique_methods);}
