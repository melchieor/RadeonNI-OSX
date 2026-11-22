/* Experimental compatibility for GCC runtime objects built against Leopard.
 * These forward to Tiger's legacy libc and do not establish identical UNIX03
 * behavior. Do not ship without operation-specific compatibility validation. */
#include <stdlib.h>
#include <stdio.h>
#include <wchar.h>
#include <time.h>
#include <unistd.h>
#include <pthread.h>

double rdn_tiger_strtod(const char *s, char **end) __asm__("_strtod$UNIX2003");
double rdn_tiger_strtod(const char *s, char **end) { return strtod(s,end); }
float rdn_tiger_strtof(const char *s, char **end) __asm__("_strtof$UNIX2003");
float rdn_tiger_strtof(const char *s, char **end) { return strtof(s,end); }
size_t rdn_tiger_wcsftime(wchar_t *s,size_t n,const wchar_t *format,const struct tm *t) __asm__("_wcsftime$UNIX2003");
size_t rdn_tiger_wcsftime(wchar_t *s,size_t n,const wchar_t *format,const struct tm *t) { return wcsftime(s,n,format,t); }
int rdn_tiger_fputs(const char *s,FILE *f) __asm__("_fputs$UNIX2003");
int rdn_tiger_fputs(const char *s,FILE *f) { return fputs(s,f); }
int rdn_tiger_mutexattr_destroy(pthread_mutexattr_t *p) __asm__("_pthread_mutexattr_destroy$UNIX2003");
int rdn_tiger_mutexattr_destroy(pthread_mutexattr_t *p) { return pthread_mutexattr_destroy(p); }
ssize_t rdn_tiger_write(int fd,const void *buf,size_t n) __asm__("_write$UNIX2003");
ssize_t rdn_tiger_write(int fd,const void *buf,size_t n) { return write(fd,buf,n); }
