/* Scripted mock transport for the Nuxel Heimdall end-session unit tests.
 *
 * No libusb, no device. Every receive/send outcome is scripted so the exact
 * classification can be asserted for each failure mode.
 */
#ifndef NUXEL_MOCK_TRANSPORT_H
#define NUXEL_MOCK_TRANSPORT_H

#include "NuxelSession.h"

#include <deque>
#include <string>
#include <vector>

namespace nuxel_test
{
	struct ReceiveStep
	{
		int  result;                 // negative == libusb-style error, >= 0 == bytes
		unsigned int responseType;   // used when result >= 4
		bool malformedShort;         // write only 2 bytes of a "response type"
		int  explicitLength;         // if >= 0, report this many bytes (size mismatch tests)

		ReceiveStep(int result, unsigned int responseType = 0,
		            bool malformedShort = false, int explicitLength = -1)
			: result(result), responseType(responseType),
			  malformedShort(malformedShort), explicitLength(explicitLength)
		{
		}
	};

	class MockTransport : public Heimdall::IPacketTransport
	{
		public:

			std::deque<ReceiveStep> receiveScript;
			int sendResult;               // first send result (bytes or negative)
			int subsequentSendResult;     // result for sends after the first
			int sendCount;
			int receiveCount;

			std::vector<int> sendLengths;
			std::vector<int> sendTimeouts;
			std::vector<int> receiveTimeouts;
			std::vector<int> emptyTransferTimeouts;
			std::vector<std::string> traceNotes;

			MockTransport(void)
				: sendResult(1024), subsequentSendResult(1024),
				  sendCount(0), receiveCount(0)
			{
			}

			int SendRaw(const unsigned char *data, int length, int timeoutMs)
			{
				(void)data;
				sendCount++;
				sendLengths.push_back(length);
				sendTimeouts.push_back(timeoutMs);

				if (length == 0)
				{
					emptyTransferTimeouts.push_back(timeoutMs);
					return (0);
				}

				return (sendCount == 1) ? sendResult : subsequentSendResult;
			}

			int ReceiveRaw(unsigned char *data, int length, int timeoutMs)
			{
				receiveCount++;
				receiveTimeouts.push_back(timeoutMs);
				(void)length;

				if (receiveScript.empty())
					return (-7); // LIBUSB_ERROR_TIMEOUT

				ReceiveStep step = receiveScript.front();
				receiveScript.pop_front();

				if (step.result < 0)
					return (step.result);

				int reported = (step.explicitLength >= 0)
					? step.explicitLength
					: (step.malformedShort ? 2 : 8);

				// Never write past the caller's buffer; still report the
				// (possibly larger) length so length mismatches can be tested.
				int writable = (reported < length) ? reported : length;
				if (writable < 0)
					writable = 0;

				for (int i = 0; i < writable; i++)
					data[i] = 0;

				if (writable >= 4)
				{
					data[0] = static_cast<unsigned char>(step.responseType & 0xFF);
					data[1] = static_cast<unsigned char>((step.responseType >> 8) & 0xFF);
					data[2] = static_cast<unsigned char>((step.responseType >> 16) & 0xFF);
					data[3] = static_cast<unsigned char>((step.responseType >> 24) & 0xFF);
				}

				return (reported);
			}

			void TraceTx(const unsigned char *data, int length) { (void)data; (void)length; }
			void TraceRx(const unsigned char *data, int length) { (void)data; (void)length; }

			void TraceNote(const char *message)
			{
				traceNotes.push_back(message ? message : "");
			}
	};
}

#endif
