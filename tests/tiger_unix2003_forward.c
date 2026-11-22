/* Host-only sanity checks of forwarding code; not a Tiger libc equivalence test. */
#include <assert.h>
#include <string.h>
#include <stdio.h>
#include <stdlib.h>
#include <pthread.h>
#include <time.h>
#include <unistd.h>
#include <wchar.h>
double rdn_tiger_strtod(const char *,char **);
float rdn_tiger_strtof(const char *,char **);
size_t rdn_tiger_wcsftime(wchar_t *,size_t,const wchar_t *,const struct tm *);
int rdn_tiger_fputs(const char *,FILE *);
int rdn_tiger_mutexattr_destroy(pthread_mutexattr_t *);
ssize_t rdn_tiger_write(int,const void *,size_t);
/* Match the assembler names used by the actual shim. */
double rdn_tiger_strtod(const char *,char **) __asm__("_strtod$UNIX2003");
float rdn_tiger_strtof(const char *,char **) __asm__("_strtof$UNIX2003");
size_t rdn_tiger_wcsftime(wchar_t *,size_t,const wchar_t *,const struct tm *) __asm__("_wcsftime$UNIX2003");
int rdn_tiger_fputs(const char *,FILE *) __asm__("_fputs$UNIX2003");
int rdn_tiger_mutexattr_destroy(pthread_mutexattr_t *) __asm__("_pthread_mutexattr_destroy$UNIX2003");
ssize_t rdn_tiger_write(int,const void *,size_t) __asm__("_write$UNIX2003");
int main(void)
{
 char *end;const char *s="12.5tail";assert(rdn_tiger_strtod(s,&end)==12.5&&strcmp(end,"tail")==0);
 assert(rdn_tiger_strtof(s,&end)==12.5f&&strcmp(end,"tail")==0);
 struct tm t={0};t.tm_year=124;t.tm_mon=0;t.tm_mday=2;wchar_t out[64];
 assert(rdn_tiger_wcsftime(out,64,L"%Y-%m-%d",&t)>0&&wcscmp(out,L"2024-01-02")==0);
 FILE *f=tmpfile();assert(f);assert(rdn_tiger_fputs("test",f)>=0);rewind(f);char buf[5]={0};assert(fread(buf,1,4,f)==4&&!strcmp(buf,"test"));fclose(f);
 pthread_mutexattr_t attr;assert(!pthread_mutexattr_init(&attr));assert(!rdn_tiger_mutexattr_destroy(&attr));
 int fd[2];assert(!pipe(fd));assert(rdn_tiger_write(fd[1],"ok",2)==2);assert(read(fd[0],buf,2)==2&&!memcmp(buf,"ok",2));close(fd[0]);close(fd[1]);
 puts("host forwarding sanity passed; Tiger UNIX03 semantic equivalence not tested");return 0;
}
