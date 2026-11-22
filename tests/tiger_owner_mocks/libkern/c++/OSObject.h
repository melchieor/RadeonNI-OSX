#ifndef TEST_OSOBJECT_H
#define TEST_OSOBJECT_H
class OSObject {
public:
 mutable unsigned references;
 OSObject():references(1){}
 virtual ~OSObject(){}
 virtual void retain() const {++references;}
 virtual void release() const {--references;}
};
#endif
