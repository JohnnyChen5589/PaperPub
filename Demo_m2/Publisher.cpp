#include <dds/DCPS/Service_Participant.h>
#include <dds/DCPS/Marked_Default_Qos.h>
#include <dds/DCPS/PublisherImpl.h>
#include <dds/DCPS/transport/tcp/TcpInst.h>
#include "dds/DCPS/StaticIncludes.h"
 
#include <ace/streams.h>
 
#include "DemoTypeSupportImpl.h"

//--socket import--
#include <iostream>
#include <cstdlib>
#include <cstring>
#include <unistd.h>
#include <sys/socket.h>
#include <netinet/in.h>
#include <arpa/inet.h>
#include <netdb.h>
#include <fcntl.h>
#include <sys/epoll.h>

// 最大Socket連線數 10
#define MAX_EVENTS 10
// Socket Server port
#define PORT 12349
//--

using namespace DemoIdlModule;
 
 
int ACE_TMAIN(int argc, ACE_TCHAR* argv[]) {
    try {
        // 發送自 Socket client 的資料
        char *server_message = "Hello from server!";

        // 創建Socket server
        int server_fd = socket(AF_INET, SOCK_DGRAM, 0);
        if (server_fd < 0) {
            std::cerr << "Failed to create socket" << std::endl;
            throw ("Unable to connect 1");
        }
        // 設定Socket server如何通訊 讓其可以接收多client連線
        int option = 1;
        if (setsockopt(server_fd, SOL_SOCKET, SO_REUSEADDR, &option, sizeof(option)) < 0) {
            std::cerr << "Failed to set socket options" << std::endl;
            throw ("Unable to connect 2");
        }

        // 設定Socket server參數
        struct sockaddr_in server_address;
        memset(&server_address, 0, sizeof(server_address));
        server_address.sin_family = AF_INET;
        server_address.sin_addr.s_addr = INADDR_ANY;
        server_address.sin_port = htons(PORT);

        // 綁定socket server位置
        if (bind(server_fd, (struct sockaddr*)&server_address, sizeof(server_address)) < 0) {
            std::cerr << "Failed to bind socket to port " << std::endl;
            throw ("Unable to connect 3");
        }

        // 監聽socket server port
        /*if (listen(server_fd, SOMAXCONN) < 0) {
            std::cerr << "Failed to start listening on port " << std::endl;
            throw ("Unable to connect 4");
        }*/

        // 創建輪詢(一種系統機制)
        int epoll_fd = epoll_create1(0);
        if (epoll_fd < 0) {
            std::cerr << "Failed to create epoll file descriptor" << std::endl;
            throw ("Unable to connect 5");
        }

        // 輪詢綁定Socket client
        struct epoll_event event, events[MAX_EVENTS - 1];
        event.events = EPOLLIN;
        event.data.fd = server_fd;
        if (epoll_ctl(epoll_fd, EPOLL_CTL_ADD, server_fd, &event) < 0) {
            std::cerr << "Failed to add server socket to epoll" << std::endl;
            throw ("Unable to connect 6");
        }

        // 參與者初始化
        argv[1] = "-DCPSConfigFile";
        argv[2] = "config_Pub.ini";
        argc = 3;
 
        // 參與者初始化
        DDS::DomainParticipantFactory_var dpf =
            TheParticipantFactoryWithArgs(argc, argv);
 
        DDS::DomainParticipant_var participant =
            dpf->create_participant(111,
                PARTICIPANT_QOS_DEFAULT,
                DDS::DomainParticipantListener::_nil(),
                ::OpenDDS::DCPS::DEFAULT_STATUS_MASK);
        if (CORBA::is_nil(participant.in())) {
            cerr << "create_participant failed." << endl;
            throw ("Unable to connect 7");
        }
 
        // 註冊數據類型
        //idl文件指定Topic
        DemoTopic2TypeSupportImpl* servant = new  DemoTopic2TypeSupportImpl();//DemoTopic2TypeSupportImpl idl指定Topic
        OpenDDS::DCPS::LocalObject_var safe_servant = servant;
 
        if (DDS::RETCODE_OK != servant->register_type(participant.in(), "")) {
            cerr << "register_type failed." << endl;
            exit(1);
        }
 
        // 創建主題
        CORBA::String_var type_name = servant->get_type_name();
 
        DDS::TopicQos topic_qos;
        participant->get_default_topic_qos(topic_qos);
        DDS::Topic_var topic =
            participant->create_topic("Movie Discussion List",
                type_name.in(),
                topic_qos,
                DDS::TopicListener::_nil(),
                ::OpenDDS::DCPS::DEFAULT_STATUS_MASK);
        if (CORBA::is_nil(topic.in())) {
            cerr << "create_topic failed." << endl;
            exit(1);
        }
 
        // 創建Publisher
        DDS::Publisher_var pub =
            participant->create_publisher(PUBLISHER_QOS_DEFAULT,
                DDS::PublisherListener::_nil(),
                ::OpenDDS::DCPS::DEFAULT_STATUS_MASK);
        if (CORBA::is_nil(pub.in())) {
            cerr << "create_publisher failed." << endl;
            exit(1);
        }
 
        // 創建DataWriter
        DDS::DataWriterQos dw_qos;
        pub->get_default_datawriter_qos(dw_qos);
        DDS::DataWriter_var dw =
            pub->create_datawriter(topic.in(),
                dw_qos,
                DDS::DataWriterListener::_nil(),
                ::OpenDDS::DCPS::DEFAULT_STATUS_MASK);
        if (CORBA::is_nil(dw.in())) {
            cerr << "create_datawriter failed." << endl;
            exit(1);
        }

        //DemoTopic2DataWriter_var idl指定DataWriter
        DemoTopic2DataWriter_var message_dw
            = DemoTopic2DataWriter::_narrow(dw.in());
        
        // 取得 DomainParticipant 的預設 Publisher QoS:
        DDS::PublisherQos pub_qos;
        DDS::ReturnCode_t ret;
        ret = participant->get_default_publisher_qos(pub_qos);
 
        if (DDS::RETCODE_OK != ret) {
            std::cerr << "Could not get default publisher QoS" << std::endl;
        }
 
        // 取得 DomainParticipant 的預設 Subscriber QoS:
        DDS::SubscriberQos sub_qos;
        ret = participant->get_default_subscriber_qos(sub_qos);
        if (DDS::RETCODE_OK != ret) {
            std::cerr << "Could not get default subscriber QoS" << std::endl;
        }
 
        // 取得 DomainParticipant 的預設 Topic QoS:
        DDS::TopicQos topic_qos2;
        ret = participant->get_default_topic_qos(topic_qos2);
        if (DDS::RETCODE_OK != ret) {
            std::cerr << "Could not get default topic QoS" << std::endl;
        }
 
        // 取得 DomainParticipant 的預設 QoS 來自 DomainParticipantFactory:
        DDS::DomainParticipantQos dp_qos;
        ret = dpf->get_default_participant_qos(dp_qos);
        if (DDS::RETCODE_OK != ret) {
            std::cerr << "Could not get default participant QoS" << std::endl;
        }
 
        // 取得 DataWriter 的預設 QoS 來自 Publisher:
        DDS::DataWriterQos dw_qos2;
        ret = pub->get_default_datawriter_qos(dw_qos2);
        if (DDS::RETCODE_OK != ret) {
            std::cerr << "Could not get default data writer QoS" << std::endl;
        }
        
 
        // 數據設置
        DemoTopic2 message;//來自idl文件中的Topic key
        message.id = 99;
        ::DDS::InstanceHandle_t handle = message_dw->register_instance(message);
        message.counter = 0;
        //char tMsg[50] = {0};
        char buffer[1024] = {0};

        while (1)
        {
            // Socket server發送和接收數據
            int num_events = epoll_wait(epoll_fd, events, MAX_EVENTS - 1, -1);
            for (int i = 0; i < num_events; ++i) {
                if (events[i].data.fd == server_fd) {
                    struct sockaddr_in client_addr;
                    socklen_t addr_len = sizeof(client_addr);
                    memset(buffer, 0, sizeof(buffer));

                    // 使用recvfrom接收數據
                    int num_bytes = recvfrom(server_fd, buffer, sizeof(buffer), 0, (struct sockaddr*)&client_addr, &addr_len);
                    if (num_bytes < 0) {
                        std::cerr << "Failed to receive data from client" << std::endl;
                        continue;
                    }
                    
                    std::cout << buffer << std::endl;
                    //
                    // 使用sendto發送給client
                    sendto(server_fd, server_message, strlen(server_message), 0, (struct sockaddr*)&client_addr, addr_len);

                    // 處理接收到的數據
                    if (num_bytes == 0) {
                        std::cout << "Client disconnected" << std::endl;
                    } else {
                        // 公佈數據資料
                        message.counter++;
                        message.text = ::TAO::String_Manager(buffer);
                        message_dw->write(message, handle);
                        std::cout << "Received " << num_bytes << " bytes from client: " << buffer << std::endl;
                    }
                }
            }
        }
        
 
        // 清理
        participant->delete_contained_entities();
        dpf->delete_participant(participant);
        TheServiceParticipant->shutdown();
    }
    catch (CORBA::Exception& e)
    {
        cerr << "PUB: Exception caught in main.cpp:" << endl << e << endl;
        exit(1);
    }
 
    return 0;
}
