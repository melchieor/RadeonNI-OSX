; Experimental Tiger-only thunks for inherited methods emitted by the
; cross-compiler. Targets were resolved from the 10.4.11 kernel/family
; vtables. Runtime/loader behavior still requires native validation.
; SPDX-License-Identifier: MIT
	.text
	.align 2
	.globl __ZN12IOUserClient4initEv
__ZN12IOUserClient4initEv:
	lis r12,hi16(__ZN8OSObject4initEv)
	ori r12,r12,lo16(__ZN8OSObject4initEv)
	mtctr r12
	bctr
	.globl __ZN12IOUserClient4initEP12OSDictionary
__ZN12IOUserClient4initEP12OSDictionary:
	lis r12,hi16(__ZN15IORegistryEntry4initEP12OSDictionary)
	ori r12,r12,lo16(__ZN15IORegistryEntry4initEP12OSDictionary)
	mtctr r12
	bctr
	.globl __ZN11IOPCIDevice13setPropertiesEP8OSObject
__ZN11IOPCIDevice13setPropertiesEP8OSObject:
	lis r12,hi16(__ZN15IORegistryEntry13setPropertiesEP8OSObject)
	ori r12,r12,lo16(__ZN15IORegistryEntry13setPropertiesEP8OSObject)
	mtctr r12
	bctr
