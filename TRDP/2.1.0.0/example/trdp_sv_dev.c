/**********************************************************************************************************************/
/**
 * @file            sendHello.c
 *
 * @brief           Demo application for TRDP
 *
 * @note            Project: TCNOpen TRDP prototype stack
 *
 * @author          Bernd Loehr and Florian Weispfenning, NewTec GmbH
 *
 * @remarks This Source Code Form is subject to the terms of the Mozilla Public License, v. 2.0.
 *          If a copy of the MPL was not distributed with this file, You can obtain one at http://mozilla.org/MPL/2.0/.
 *          Copyright Bombardier Transportation Inc. or its subsidiaries and others, 2013. All rights reserved.
 *
 * $Id: sendHello.c 2280 2021-08-09 08:50:18Z s-bender $
 *
 *      SB 2021-08-09: Compiler warnings
 *      BL 2018-03-06: Ticket #101 Optional callback function on PD send
 *      BL 2017-06-30: Compiler warnings, local prototypes added
 */

/***********************************************************************************************************************
 * INCLUDES
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#if defined (POSIX)
#include <unistd.h>
#include <sys/select.h>
#elif (defined (WIN32) || defined (WIN64))
#include "getopt.h"
#endif

#include "trdp_if_light.h"
#include "vos_thread.h"
#include "vos_utils.h"

// socket
#include <arpa/inet.h>
#include <sys/socket.h>
#define SERVER_PORT 12346
#define CLIENT_PORT 12345
//---socket

// threads handle
#include <pthread.h>

/***********************************************************************************************************************
 * DEFINITIONS
 */
#define APP_VERSION     "1.4"

#define DATA_MAX        8192u

#define PD_COMID_PUB        1000u
#define PD_COMID_SUB        1002u
#define PD_COMID_CYCLE_PUB  500000u             /* in us (1000000 = 1 sec) */
#define PD_COMID_CYCLE_SUB  100000u

#define OWN_IP_ADDR  "192.168.1.30"
#define DEST_IP_ADDR "192.168.1.27"

/* We use dynamic memory    */
#define RESERVED_MEMORY  160000u

/***********************************************************************************************************************
 * PROTOTYPES
 */
void dbgOut (void *,
             TRDP_LOG_T,
             const  CHAR8 *,
             const  CHAR8 *,
             UINT16,
             const  CHAR8 *);
void    usage (const char *);
void    myPDcallBack (void *,
                      TRDP_APP_SESSION_T,
                      const TRDP_PD_INFO_T *,
                      UINT8 *,
                      UINT32 );

/**********************************************************************************************************************/
/** callback routine for TRDP logging/error output
 *
 *  @param[in]      pRefCon             user supplied context pointer
 *  @param[in]      category            Log category (Error, Warning, Info etc.)
 *  @param[in]      pTime               pointer to NULL-terminated string of time stamp
 *  @param[in]      pFile               pointer to NULL-terminated string of source module
 *  @param[in]      LineNumber          line
 *  @param[in]      pMsgStr             pointer to NULL-terminated string
 *
 *  @retval         none
 */
void dbgOut (
    void        *pRefCon,
    TRDP_LOG_T  category,
    const CHAR8 *pTime,
    const CHAR8 *pFile,
    UINT16      LineNumber,
    const CHAR8 *pMsgStr)
{
    const char *catStr[] = {"**Error:", "Warning:", "   Info:", "  Debug:", "   User:"};
    CHAR8       *pF = strrchr(pFile, VOS_DIR_SEP);
    printf("%s %s %s:%d %s",
           strrchr(pTime, '-') + 1,
           catStr[category],
           (pF == NULL)? "" : pF + 1,
           LineNumber,
           pMsgStr);
}

/* Print a sensible usage message */
void usage (const char *appName)
{
    printf("Usage of %s\n", appName);
    printf("This tool sends PD messages to an ED.\n"
           "Arguments are:\n"
           "-o <own IP address> (default INADDR_ANY)\n"
           "-t <target IP address>\n"
           "-c <comId_pub> (default 0)\n"
           "-s <cycle time> (default 1000000 [us])\n"
           "-e send empty request\n"
           "-d <custom string to send> (default: 'Hello World')\n"
           "-v print version and quit\n"
           );
}

int *server_function(void *arg)
{
    unsigned int            ip[4];
    TRDP_APP_SESSION_T      appHandle; /*    Our identifier to the library instance    */
    TRDP_PUB_T              pubHandle; /*    Our identifier to the publication         */
    
    UINT32                  comId_pub           = PD_COMID_PUB;

    UINT32                  interval        = PD_COMID_CYCLE_PUB;
    TRDP_ERR_T              err;
    TRDP_PD_CONFIG_T        pdConfiguration =
    {NULL, NULL, TRDP_PD_DEFAULT_SEND_PARAM, TRDP_FLAGS_NONE, 1000000u, TRDP_TO_SET_TO_ZERO, 0};
    TRDP_MEM_CONFIG_T       dynamicConfig   = {NULL, RESERVED_MEMORY, {0}};
    TRDP_PROCESS_CONFIG_T   processConfig   = {"Me", "", "", TRDP_PROCESS_DEFAULT_CYCLE_TIME, 0u, TRDP_OPTION_BLOCK};
    UINT32                  ownIP           = 0u;
    int                     rv = 0;
    UINT32                  destIP = 0u;

    /*    Generate some data, that we want to send, when nothing was specified. */
    UINT8                   *outputBuffer;
    UINT8                   buffer[DATA_MAX]   = "buffer No Data";
    UINT32                  outputBufferSize        = 1432u;

    UINT32  sendSize;
    TRDP_PD_INFO_T myPDInfo;


    /* IP Address*/
    const char* ownIP_str = OWN_IP_ADDR;
    const char* destIP_str = DEST_IP_ADDR;

    sscanf(ownIP_str, "%u.%u.%u.%u", &ip[3], &ip[2], &ip[1], &ip[0]);
    ownIP = (ip[3] << 24) | (ip[2] << 16) | (ip[1] << 8) | ip[0];
    sscanf(destIP_str, "%u.%u.%u.%u", &ip[3], &ip[2], &ip[1], &ip[0]);
    destIP = (ip[3] << 24) | (ip[2] << 16) | (ip[1] << 8) | ip[0];

    // socket
    // server
    int sockfd;
    struct sockaddr_in server_addr;

    // Create socket
    sockfd = socket(AF_INET, SOCK_DGRAM, 0);
    if (sockfd == -1) {
        perror("Error creating socket");
        exit(EXIT_FAILURE);
    }

    // Bind to server address
    memset(&server_addr, 0, sizeof(server_addr));
    server_addr.sin_family = AF_INET;
    server_addr.sin_addr.s_addr = htonl(INADDR_ANY);
    server_addr.sin_port = htons(SERVER_PORT);

    if (bind(sockfd, (struct sockaddr *)&server_addr, sizeof(server_addr)) == -1) {
        perror("Error binding");
        close(sockfd);
        exit(EXIT_FAILURE);
    }

    printf("Server listening on port %d...\n", SERVER_PORT);

    outputBuffer = buffer;
    
    if (destIP == 0)
    {
        fprintf(stderr, "No destination address given!\n");
        return 1;
    }

    /*    Init the library  */
    if (tlc_init(&dbgOut,                              /* no logging    */
                 NULL,
                 &dynamicConfig) != TRDP_NO_ERR)    /* Use application supplied memory    */
    {
        printf("Initialization error\n");
        return 1;
    }

    /*    Open a session  */
    if (tlc_openSession(&appHandle,
                        ownIP, 0,               /* use default IP address           */
                        NULL,                   /* no Marshalling                   */
                        &pdConfiguration, NULL, /* system defaults for PD and MD    */
                        &processConfig) != TRDP_NO_ERR)
    {
        vos_printLogStr(VOS_LOG_USR, "Initialization error\n");
        return 1;
    }

    /*    Copy the packet into the internal send queue, prepare for sending.    */
    /*    If we change the data, just re-publish it    */
    err = tlp_publish(  appHandle,                  /*    our application identifier    */
                        &pubHandle,                 /*    our pulication identifier     */
                        NULL, NULL,
                        0u,
                        comId_pub,                      /*    ComID to send                 */
                        0u,                         /*    etbTopoCnt = 0 for local consist only     */
                        0u,                         /*    opTopoCnt = 0 for non-directinal data     */
                        ownIP,                      /*    default source IP             */
                        destIP,                     /*    where to send to              */
                        interval,                   /*    Cycle time in us              */
                        0u,                         /*    not redundant                 */
                        TRDP_FLAGS_NONE,            /*    Use callback for errors       */
                        NULL,                       /*    default qos and ttl           */
                        (UINT8 *)outputBuffer,      /*    initial data                  */
                        outputBufferSize            /*    data size                     */
                        );


    if (err != TRDP_NO_ERR)
    {
        vos_printLog(VOS_LOG_USR, "tlp_publish error (%s)\n", vos_getErrorString((VOS_ERR_T)err));
        tlc_terminate();
        return 1;
    }

    /*
     Finish the setup.
     On non-high-performance targets, this is a no-op.
     This call is necessary if HIGH_PERF_INDEXED is defined. It will create the internal index tables for faster access.
     It should be called after the last publisher and subscriber has been added.
     Maybe tlc_activateSession would be a better name.If HIGH_PERF_INDEXED is set, this call will create the internal index tables for fast telegram access
     */

    err = tlc_updateSession(appHandle);
    if (err != TRDP_NO_ERR)
    {
        vos_printLog(VOS_LOG_USR, "tlc_updateSession error (%s)\n", vos_getErrorString((VOS_ERR_T)err));
        tlc_terminate();
        return 1;
    }

    /*
       Enter the main processing loop.
     */
    while (1)
    {
        TRDP_FDS_T          rfds;
        INT32               noDesc;
        TRDP_TIME_T         tv;
        const TRDP_TIME_T   max_tv  = {0, PD_COMID_CYCLE_PUB * 3};
        const TRDP_TIME_T   min_tv  = {0, PD_COMID_CYCLE_PUB};

        /*
           Prepare the file descriptor set for the select call.
           Additional descriptors can be added here.
         */
        FD_ZERO(&rfds);
        /* FD_SET(pd_fd, &rfds); */

        /*
           Compute the min. timeout value for select.
           This way we can guarantee that PDs are sent in time
           with minimum CPU load and minimum jitter.
         */
        tlc_getInterval(appHandle, &tv, &rfds, &noDesc);

        /*
           The wait time for select must consider cycle times and timeouts of
           the PD packets received or sent.
           If we need to poll something faster than the lowest PD cycle,
           we need to set the maximum time out our self.
         */
        if (vos_cmpTime(&tv, &max_tv) > 0)
        {
            tv = max_tv;
        }
        else if (vos_cmpTime(&tv, &min_tv) < 0)
        {
            tv = min_tv;
        }

        /*
           Select() will wait for ready descriptors or time out,
           what ever comes first.
         */
        rv = vos_select(noDesc + 1, &rfds, NULL, NULL, &tv);

        /*
           Check for overdue PDs (sending and receiving)
           Send any pending PDs if it's time...
           Detect missing PDs...
           'rv' will be updated to show the handled events, if there are
           more than one...
           The callback function will be called from within the tlc_process
           function (in it's context and thread)!
         */
        (void) tlc_process(appHandle, &rfds, &rv);

        /* Handle other ready descriptors... */
        if (rv > 0)
        {
            vos_printLogStr(VOS_LOG_USR, "other descriptors were ready\n");
        }
        else
        {
            fprintf(stdout, ".");
            fflush(stdout);
        }
        
        //pub
        // socket server
        memset(buffer, 0, sizeof(buffer));
        ssize_t recv_len = recvfrom(sockfd, buffer, sizeof(buffer), 0,
                                (struct sockaddr *)&server_addr, sizeof(server_addr));
        if (recv_len > 0) {
            buffer[recv_len] = '\0';
            printf("recv socket to trdp: %s\n", buffer);
        }
        //---socket server
        sprintf((char *)outputBuffer, buffer);
        outputBufferSize = (UINT32) strlen((char *)outputBuffer);
        
        err = tlp_put(appHandle, pubHandle, outputBuffer, outputBufferSize);
        if (err != TRDP_NO_ERR)
        {
            vos_printLogStr(VOS_LOG_ERROR, "put pd error\n");
            rv = 1;
            break;
        }
        
        
    }
    /*
     *    We always clean up behind us!
     */
    tlp_unpublish(appHandle, pubHandle);
    tlc_closeSession(appHandle);
    tlc_terminate();

    return rv;
}

int *client_function(void *arg)
{
    unsigned int            ip[4];
    TRDP_APP_SESSION_T      appHandle; /*    Our identifier to the library instance    */
    TRDP_PUB_T              pubHandle; /*    Our identifier to the publication         */
    //sub
    TRDP_SUB_T              subHandle;  /*    Our identifier to the subscription    */

    //sub
    UINT32                  comId_sub           = PD_COMID_SUB;

    UINT32                  interval        = PD_COMID_CYCLE_SUB;
    TRDP_ERR_T              err;
    TRDP_PD_CONFIG_T        pdConfiguration =
    {NULL, NULL, TRDP_PD_DEFAULT_SEND_PARAM, TRDP_FLAGS_NONE, 1000000u, TRDP_TO_SET_TO_ZERO, 0};
    TRDP_MEM_CONFIG_T       dynamicConfig   = {NULL, RESERVED_MEMORY, {0}};
    TRDP_PROCESS_CONFIG_T   processConfig   = {"Me", "", "", TRDP_PROCESS_DEFAULT_CYCLE_TIME, 0u, TRDP_OPTION_BLOCK};
    UINT32                  ownIP           = 0u;
    int                     rv = 0;
    UINT32                  destIP = 0u;

    // sub
    UINT8                   gBuffer[DATA_MAX]   = "gbuffer No Data";
    
    UINT32  receivedSize;
    TRDP_PD_INFO_T myPDInfo;

    /* IP Address*/
    const char* ownIP_str = OWN_IP_ADDR;
    const char* destIP_str = DEST_IP_ADDR;

    sscanf(ownIP_str, "%u.%u.%u.%u", &ip[3], &ip[2], &ip[1], &ip[0]);
    ownIP = (ip[3] << 24) | (ip[2] << 16) | (ip[1] << 8) | ip[0];
    sscanf(destIP_str, "%u.%u.%u.%u", &ip[3], &ip[2], &ip[1], &ip[0]);
    destIP = (ip[3] << 24) | (ip[2] << 16) | (ip[1] << 8) | ip[0];

    // socket
    // client
    int sockfd2;
    struct sockaddr_in client_addr;

    // Create socket
    sockfd2 = socket(AF_INET, SOCK_DGRAM, 0);
    if (sockfd2 == -1) {
        perror("Error creating socket");
        exit(EXIT_FAILURE);
    }

    // Set client address
    memset(&client_addr, 0, sizeof(client_addr));
    client_addr.sin_family = AF_INET;
    client_addr.sin_addr.s_addr = inet_addr(ownIP_str);
    client_addr.sin_port = htons(CLIENT_PORT);
    //---socket

    if (destIP == 0)
    {
        fprintf(stderr, "No destination address given!\n");
        return 1;
    }

    /*    Init the library  */
    if (tlc_init(&dbgOut,                              /* no logging    */
                 NULL,
                 &dynamicConfig) != TRDP_NO_ERR)    /* Use application supplied memory    */
    {
        printf("Initialization error\n");
        return 1;
    }

    /*    Open a session  */
    if (tlc_openSession(&appHandle,
                        ownIP, 0,               /* use default IP address           */
                        NULL,                   /* no Marshalling                   */
                        &pdConfiguration, NULL, /* system defaults for PD and MD    */
                        &processConfig) != TRDP_NO_ERR)
    {
        vos_printLogStr(VOS_LOG_USR, "Initialization error\n");
        return 1;
    }

    err = tlp_subscribe( appHandle,                 /*    our application identifier            */
                         &subHandle,                /*    our subscription identifier           */
                         NULL,                      /*    user reference                        */
                         NULL,                      /*    callback functiom                     */
                         0u,
                         comId_sub,                     /*    ComID                                 */
                         0,                         /*    etbTopoCnt: local consist only        */
                         0,                         /*    opTopoCnt                             */
                         VOS_INADDR_ANY, VOS_INADDR_ANY,    /*    Source IP filter              */
                         destIP,                     /*    Default destination    (or MC Group)  */
                         TRDP_FLAGS_DEFAULT,        /*    TRDP flags                            */
                         NULL,                      /*    default interface                    */
                         PD_COMID_CYCLE_SUB * 3,        /*    Time out in us                        */
                         TRDP_TO_SET_TO_ZERO        /*    delete invalid data on timeout        */
                         );

    
    if (err != TRDP_NO_ERR)
    {
        vos_printLog(VOS_LOG_USR, "tlp_publish error (%s)\n", vos_getErrorString((VOS_ERR_T)err));
        tlc_terminate();
        return 1;
    }

    /*
     Finish the setup.
     On non-high-performance targets, this is a no-op.
     This call is necessary if HIGH_PERF_INDEXED is defined. It will create the internal index tables for faster access.
     It should be called after the last publisher and subscriber has been added.
     Maybe tlc_activateSession would be a better name.If HIGH_PERF_INDEXED is set, this call will create the internal index tables for fast telegram access
     */

    err = tlc_updateSession(appHandle);
    if (err != TRDP_NO_ERR)
    {
        vos_printLog(VOS_LOG_USR, "tlc_updateSession error (%s)\n", vos_getErrorString((VOS_ERR_T)err));
        tlc_terminate();
        return 1;
    }

    /*
       Enter the main processing loop.
     */
    while (1)
    {
        TRDP_FDS_T          rfds;
        INT32               noDesc;
        TRDP_TIME_T         tv;
        const TRDP_TIME_T   max_tv  = {0, PD_COMID_CYCLE_SUB * 3};
        const TRDP_TIME_T   min_tv  = {0, PD_COMID_CYCLE_SUB};

        /*
           Prepare the file descriptor set for the select call.
           Additional descriptors can be added here.
         */
        FD_ZERO(&rfds);
        /* FD_SET(pd_fd, &rfds); */

        /*
           Compute the min. timeout value for select.
           This way we can guarantee that PDs are sent in time
           with minimum CPU load and minimum jitter.
         */
        tlc_getInterval(appHandle, &tv, &rfds, &noDesc);

        /*
           The wait time for select must consider cycle times and timeouts of
           the PD packets received or sent.
           If we need to poll something faster than the lowest PD cycle,
           we need to set the maximum time out our self.
         */
        if (vos_cmpTime(&tv, &max_tv) > 0)
        {
            tv = max_tv;
        }
        else if (vos_cmpTime(&tv, &min_tv) < 0)
        {
            tv = min_tv;
        }

        /*
           Select() will wait for ready descriptors or time out,
           what ever comes first.
         */
        rv = vos_select(noDesc + 1, &rfds, NULL, NULL, &tv);

        /*
           Check for overdue PDs (sending and receiving)
           Send any pending PDs if it's time...
           Detect missing PDs...
           'rv' will be updated to show the handled events, if there are
           more than one...
           The callback function will be called from within the tlc_process
           function (in it's context and thread)!
         */
        (void) tlc_process(appHandle, &rfds, &rv);

        /* Handle other ready descriptors... */
        if (rv > 0)
        {
            vos_printLogStr(VOS_LOG_USR, "other descriptors were ready\n");
        }
        else
        {
            fprintf(stdout, ".");
            fflush(stdout);
        }
        
        //sub
        memset(gBuffer, 0, sizeof(gBuffer));
        receivedSize = sizeof(gBuffer);
        err = tlp_get(appHandle,
                    subHandle,
                    &myPDInfo,
                    (UINT8 *) gBuffer,
                    &receivedSize);
        
        if ((TRDP_NO_ERR == err)
            && (receivedSize > 0))
        {
            // socket client
            // Send message to server
            sendto(sockfd2, gBuffer, strlen(gBuffer), 0,
                (struct sockaddr *)&client_addr, sizeof(client_addr));

            printf("recv trdp to socket: %s\n", gBuffer);
            //---socket client

            /*vos_printLogStr(VOS_LOG_USR, "\nMessage reveived:\n");
            vos_printLog(VOS_LOG_USR, "Type = %c%c, ", myPDInfo.msgType >> 8, myPDInfo.msgType & 0xFF);
            vos_printLog(VOS_LOG_USR, "Seq  = %u, ", myPDInfo.seqCount);
            vos_printLog(VOS_LOG_USR, "with %d Bytes:\n", receivedSize);
            vos_printLog(VOS_LOG_USR, "   %02hhx %02hhx %02hhx %02hhx %02hhx %02hhx %02hhx %02hhx\n",
                gBuffer[0], gBuffer[1], gBuffer[2], gBuffer[3],
                gBuffer[4], gBuffer[5], gBuffer[6], gBuffer[7]);
            vos_printLog(VOS_LOG_USR, "   %02hhx %02hhx %02hhx %02hhx %02hhx %02hhx %02hhx %02hhx\n",
                gBuffer[8], gBuffer[9], gBuffer[10], gBuffer[11],
                gBuffer[12], gBuffer[13], gBuffer[14], gBuffer[15]);
            vos_printLog(VOS_LOG_USR, "%s\n", gBuffer);*/

        }
        else if (TRDP_NO_ERR == err)
        {
            vos_printLogStr(VOS_LOG_USR, "\nMessage reveived Err:\n");
            vos_printLog(VOS_LOG_USR, "Type = %c%c - ", myPDInfo.msgType >> 8, myPDInfo.msgType & 0xFF);
            vos_printLog(VOS_LOG_USR, "Seq  = %u\n", myPDInfo.seqCount);
        }
        else if (TRDP_TIMEOUT_ERR == err)
        {
            vos_printLogStr(VOS_LOG_INFO, "Packet timed out\n");
        }
        else if (TRDP_NODATA_ERR == err)
        {
            vos_printLogStr(VOS_LOG_INFO, "No data yet\n");
        }
        else
        {
            vos_printLog(VOS_LOG_ERROR, "PD GET ERROR: %d\n", err);
        }
    }
    /*
     *    We always clean up behind us!
     */
    tlp_unsubscribe(appHandle, subHandle);
    tlc_closeSession(appHandle);
    tlc_terminate();

    return rv;
}

/**********************************************************************************************************************/
/** main entry
 *
 *  @retval         0        no error
 *  @retval         1        some error
 */
int main ()
{
    pthread_t server_thread, client_thread;
    
    pthread_create(&server_thread, NULL, server_function, NULL);
    pthread_create(&client_thread, NULL, client_function, NULL);
    
    pthread_join(server_thread, NULL);
    pthread_join(client_thread, NULL);
    
    return 0;
}
