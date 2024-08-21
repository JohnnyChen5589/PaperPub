// -*- C++ -*-
//
#include "DataReaderListener.h"
#include "DemoTypeSupportC.h"
#include "DemoTypeSupportImpl.h"
#include <dds/DCPS/Service_Participant.h>
#include <ace/streams.h>

// --socket
#include <iostream>
#include <cstring>
#include <sys/socket.h>
#include <netinet/in.h>
#include <arpa/inet.h>
#include <unistd.h>
//--

using namespace DemoIdlModule;
 
DataReaderListener::DataReaderListener() : num_reads_(0)
{
    sockfd = socket(AF_INET, SOCK_DGRAM, 0);
    if (sockfd < 0) {
        std::cerr << "Error creating socket." << std::endl;
    }

    memset(&serverAddr, 0, sizeof(serverAddr));
    serverAddr.sin_family = AF_INET;
    serverAddr.sin_port = htons(PORT);
    serverAddr.sin_addr.s_addr = inet_addr(SERVER_IP);
}
 
DataReaderListener::~DataReaderListener()
{
}
 
void DataReaderListener::on_data_available(DDS::DataReader_ptr reader)
{
    ++num_reads_;
 
    try {
        DemoTopic1DataReader_var message_dr = DemoTopic1DataReader::_narrow(reader);
        if (CORBA::is_nil(message_dr.in())) {
            cerr << "read: _narrow failed." << endl;
            exit(1);
        }
        DemoTopic1 message;
        DDS::SampleInfo si;
        DDS::ReturnCode_t status = message_dr->take_next_sample(message, si);        
        if (status == DDS::RETCODE_OK) {
            std::string message_str(message.text);
            const char* msg = message_str.c_str();
            sendto(sockfd, msg, strlen(msg), 0, (struct sockaddr*)&serverAddr, sizeof(serverAddr));
            cout << "Message: id    = " << message.id << endl
                << "         DemoTopic1_Counter = " << message.counter << endl
                << "         DemoTopic1_Text = " << message.text << endl;
 
            cout << "SampleInfo.sample_rank = " << si.sample_rank << endl;
        }
        else if (status == DDS::RETCODE_NO_DATA) {
            cerr << "ERROR: reader received DDS::RETCODE_NO_DATA!" << endl;
        }
        else {
            cerr << "ERROR: read Message: Error: " << status << endl;
        }
    }
    catch (CORBA::Exception& e) {
        cerr << "Exception caught in read:" << endl << e << endl;
        exit(1);
    }
}
 
void DataReaderListener::on_requested_deadline_missed(
    DDS::DataReader_ptr,
    const DDS::RequestedDeadlineMissedStatus&)
{
    cerr << "DataReaderListener::on_requested_deadline_missed" << endl;
}
 
void DataReaderListener::on_requested_incompatible_qos(
    DDS::DataReader_ptr,
    const DDS::RequestedIncompatibleQosStatus&)
{
    cerr << "DataReaderListener::on_requested_incompatible_qos" << endl;
}
 
void DataReaderListener::on_liveliness_changed(
    DDS::DataReader_ptr,
    const DDS::LivelinessChangedStatus&)
{
    cerr << "DataReaderListener::on_liveliness_changed" << endl;
}
 
void DataReaderListener::on_subscription_matched(
    DDS::DataReader_ptr,
    const DDS::SubscriptionMatchedStatus&)
{
    cerr << "DataReaderListener::on_subscription_matched" << endl;
}
 
void DataReaderListener::on_sample_rejected(
    DDS::DataReader_ptr,
    const DDS::SampleRejectedStatus&)
{
    cerr << "DataReaderListener::on_sample_rejected" << endl;
}
 
void DataReaderListener::on_sample_lost(
    DDS::DataReader_ptr,
    const DDS::SampleLostStatus&)
{
    cerr << "DataReaderListener::on_sample_lost" << endl;
}
 
void DataReaderListener::on_subscription_disconnected(
    DDS::DataReader_ptr,
    const ::OpenDDS::DCPS::SubscriptionDisconnectedStatus&)
{
    cerr << "DataReaderListener::on_subscription_disconnected" << endl;
}
 
void DataReaderListener::on_subscription_reconnected(
    DDS::DataReader_ptr,
    const ::OpenDDS::DCPS::SubscriptionReconnectedStatus&)
{
    cerr << "DataReaderListener::on_subscription_reconnected" << endl;
}
 
void DataReaderListener::on_subscription_lost(
    DDS::DataReader_ptr,
    const ::OpenDDS::DCPS::SubscriptionLostStatus&)
{
    cerr << "DataReaderListener::on_subscription_lost" << endl;
}
 
void DataReaderListener::on_budget_exceeded(
    DDS::DataReader_ptr,
    const ::OpenDDS::DCPS::BudgetExceededStatus&)
{
    cerr << "DataReaderListener::on_budget_exceeded" << endl;
}
