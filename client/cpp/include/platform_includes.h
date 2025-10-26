#ifndef PLATFORM_INCLUDES_H
#define PLATFORM_INCLUDES_H

// 1
#include <WinSock2.h>
// 2
#include <Windows.h>
// 3
#include <WS2tcpip.h>
// 4
#include <Mstcpip.h>
// 5

#ifndef SIO_UDP_CONNRESET
#define SIO_UDP_CONNRESET _WSAIOW(IOC_VENDOR, 12)
#endif

#endif