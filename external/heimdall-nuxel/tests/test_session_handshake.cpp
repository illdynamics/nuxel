/* Nuxel Heimdall end-session state machine tests.
 *
 * These tests do not touch USB or a phone. They assert that every distinct
 * real-world outcome (timeout, disconnect, malformed reply, rejected command,
 * delayed reply, missing acknowledgement) is classified distinctly and that
 * only a positive acknowledgement is ever reported as success.
 *
 * Build/run: external/heimdall-nuxel/scripts/run-tests.sh
 */
#include "NuxelSession.h"
#include "mock_transport.h"

#include <cstdio>
#include <cstring>
#include <string>

using namespace Heimdall;
using namespace nuxel_test;

static int failures = 0;
static int checks = 0;

static void check(bool condition, const std::string& what)
{
	checks++;
	if (!condition)
	{
		failures++;
		std::fprintf(stderr, "  FAIL: %s\n", what.c_str());
	}
}

static void checkEq(long expected, long actual, const std::string& what)
{
	checks++;
	if (expected != actual)
	{
		failures++;
		std::fprintf(stderr, "  FAIL: %s (expected %ld, got %ld)\n",
		             what.c_str(), expected, actual);
	}
}

static void checkEqStr(const std::string& expected, const std::string& actual,
                       const std::string& what)
{
	checks++;
	if (expected != actual)
	{
		failures++;
		std::fprintf(stderr, "  FAIL: %s (expected \"%s\", got \"%s\")\n",
		             what.c_str(), expected.c_str(), actual.c_str());
	}
}

enum { kSendTimeout = 3000, kRecvTimeout = 3000, kRebootTimeout = 3000 };

// 1. Happy path: end session acknowledged, no reboot requested.
static void test_ok_no_reboot(void)
{
	MockTransport t;
	t.receiveScript.push_back(ReceiveStep(8, 0x67));

	SessionReport report;
	bool ok = NuxelRunEndSession(t, false, kSendTimeout, kRecvTimeout, kRebootTimeout,
	                             kNuxelEmptyTransferAfter, false, &report);

	check(ok, "ok: returns true");
	check(report.PositivelyAcknowledged(), "ok: positively acknowledged");
	checkEqStr("ok_acknowledged", report.ResultToken(), "ok: token");
	checkEqStr("none", report.FailureName(), "ok: failure name");
	checkEq(0x67, report.ackResponseType, "ok: response type decoded");
	checkEq(0, report.ackAttempts - 1, "ok: single ack attempt");
	checkEq(1, (long)t.receiveCount, "ok: one receive");
}

// 2. Happy path with reboot acknowledged.
static void test_ok_reboot(void)
{
	MockTransport t;
	t.receiveScript.push_back(ReceiveStep(8, 0x67));
	t.receiveScript.push_back(ReceiveStep(8, 0x67));

	SessionReport report;
	bool ok = NuxelRunEndSession(t, true, kSendTimeout, kRecvTimeout, kRebootTimeout,
	                             kNuxelEmptyTransferAfter, false, &report);

	check(ok, "reboot ok: returns true");
	check(report.PositivelyAcknowledged(), "reboot ok: acknowledged");
	check(report.rebootAckReceived, "reboot ok: reboot ack");
	checkEq(2, (long)t.receiveCount, "reboot ok: two receives");
}

// 3. Delayed acknowledgement (first read times out, second succeeds).
static void test_delayed_ack(void)
{
	MockTransport t;
	t.receiveScript.push_back(ReceiveStep(-7));            // LIBUSB_ERROR_TIMEOUT
	t.receiveScript.push_back(ReceiveStep(8, 0x67));

	SessionReport report;
	bool ok = NuxelRunEndSession(t, false, kSendTimeout, kRecvTimeout, kRebootTimeout,
	                             kNuxelEmptyTransferAfter, false, &report);

	check(ok, "delayed: returns true");
	check(report.DelayedAck(), "delayed: flagged delayed");
	checkEqStr("ok_delayed_ack", report.ResultToken(), "delayed: token");
	checkEq(2, (long)report.ackAttempts, "delayed: two attempts");
}

// 4. Missing acknowledgement: bounded timeout, all attempts exhausted.
static void test_missing_ack_timeout(void)
{
	MockTransport t;
	t.receiveScript.push_back(ReceiveStep(-7));
	t.receiveScript.push_back(ReceiveStep(-7));
	t.receiveScript.push_back(ReceiveStep(-7));
	t.receiveScript.push_back(ReceiveStep(-7)); // must not be consumed (bounded)

	SessionReport report;
	bool ok = NuxelRunEndSession(t, false, kSendTimeout, kRecvTimeout, kRebootTimeout,
	                             kNuxelEmptyTransferAfter, false, &report);

	check(!ok, "timeout: returns false");
	check(!report.PositivelyAcknowledged(), "timeout: not acknowledged");
	checkEqStr("timeout", report.ResultToken(), "timeout: token");
	checkEqStr("missing_acknowledgement_timeout", report.FailureName(), "timeout: failure name");
	checkEq(-7, report.lastLibusbError, "timeout: libusb error recorded");
	checkEq(3, (long)t.receiveCount, "timeout: retries are bounded to 3");
}

// 5. USB disconnect during the end-session acknowledgement.
static void test_usb_disconnect(void)
{
	MockTransport t;
	t.receiveScript.push_back(ReceiveStep(-4)); // LIBUSB_ERROR_NO_DEVICE

	SessionReport report;
	bool ok = NuxelRunEndSession(t, false, kSendTimeout, kRecvTimeout, kRebootTimeout,
	                             kNuxelEmptyTransferAfter, false, &report);

	check(!ok, "disconnect: returns false");
	checkEqStr("usb_disconnect", report.ResultToken(), "disconnect: token");
	checkEqStr("usb_disconnect", report.FailureName(), "disconnect: failure name");
	checkEq(-4, report.lastLibusbError, "disconnect: libusb error recorded");
	checkEq(1, (long)t.receiveCount, "disconnect: not retried like a timeout");
}

// 6. Malformed reply: shorter than a response type.
static void test_malformed_short(void)
{
	MockTransport t;
	t.receiveScript.push_back(ReceiveStep(8, 0x67, true /* malformedShort -> 2 bytes */));

	SessionReport report;
	bool ok = NuxelRunEndSession(t, false, kSendTimeout, kRecvTimeout, kRebootTimeout,
	                             kNuxelEmptyTransferAfter, false, &report);

	check(!ok, "malformed short: returns false");
	checkEqStr("malformed_packet", report.ResultToken(), "malformed short: token");
	checkEq(2, report.ackBytesTransferred, "malformed short: byte count recorded");
}

// 7. Malformed reply: wrong total length.
static void test_malformed_length(void)
{
	MockTransport t;
	t.receiveScript.push_back(ReceiveStep(8, 0x67, false, 16 /* reported length */));

	SessionReport report;
	bool ok = NuxelRunEndSession(t, false, kSendTimeout, kRecvTimeout, kRebootTimeout,
	                             kNuxelEmptyTransferAfter, false, &report);

	check(!ok, "malformed length: returns false");
	checkEqStr("malformed_packet", report.ResultToken(), "malformed length: token");
}

// 8. Rejected command: well-formed 8-byte reply with the wrong response type.
static void test_rejected_command(void)
{
	MockTransport t;
	t.receiveScript.push_back(ReceiveStep(8, 0x66)); // file-transfer response, not 0x67

	SessionReport report;
	bool ok = NuxelRunEndSession(t, false, kSendTimeout, kRecvTimeout, kRebootTimeout,
	                             kNuxelEmptyTransferAfter, false, &report);

	check(!ok, "rejected: returns false");
	checkEqStr("rejected_command", report.ResultToken(), "rejected: token");
	checkEqStr("rejected_command_unexpected_response", report.FailureName(), "rejected: failure name");
	check(report.ackResponseTypeKnown, "rejected: response type was decodable");
	checkEq(0x66, report.ackResponseType, "rejected: recorded wrong response type");
}

// 9. Send failure before any acknowledgement can arrive.
static void test_send_failed(void)
{
	MockTransport t;
	t.sendResult = -4; // LIBUSB_ERROR_NO_DEVICE on the control write

	SessionReport report;
	bool ok = NuxelRunEndSession(t, false, kSendTimeout, kRecvTimeout, kRebootTimeout,
	                             kNuxelEmptyTransferAfter, false, &report);

	check(!ok, "send failed: returns false");
	checkEqStr("send_failed", report.ResultToken(), "send failed: token");
	check(!report.endSessionSent, "send failed: not marked sent");
}

// 10. Reboot request: device disconnects instead of answering.
static void test_reboot_disconnect_unconfirmed(void)
{
	MockTransport t;
	t.receiveScript.push_back(ReceiveStep(8, 0x67));
	t.receiveScript.push_back(ReceiveStep(-4));

	SessionReport report;
	bool ok = NuxelRunEndSession(t, true, kSendTimeout, kRecvTimeout, kRebootTimeout,
	                             kNuxelEmptyTransferAfter, false, &report);

	check(!ok, "reboot disconnect: returns false (never assume a reboot)");
	check(!report.PositivelyAcknowledged(), "reboot disconnect: not acknowledged");
	checkEqStr("reboot_disconnect", report.ResultToken(), "reboot disconnect: token");
}

// 11. Reboot request: acknowledgement never arrives.
static void test_reboot_timeout(void)
{
	MockTransport t;
	t.receiveScript.push_back(ReceiveStep(8, 0x67));
	t.receiveScript.push_back(ReceiveStep(-7));
	t.receiveScript.push_back(ReceiveStep(-7));
	t.receiveScript.push_back(ReceiveStep(-7));

	SessionReport report;
	bool ok = NuxelRunEndSession(t, true, kSendTimeout, kRecvTimeout, kRebootTimeout,
	                             kNuxelEmptyTransferAfter, false, &report);

	check(!ok, "reboot timeout: returns false");
	checkEqStr("reboot_timeout", report.ResultToken(), "reboot timeout: token");
	check(report.endSessionAckReceived, "reboot timeout: end-session did ack");
}

// 12. Empty (zero-length) transfer placement and its bounded timeout.
static void test_empty_transfer_flags(void)
{
	MockTransport t;
	t.receiveScript.push_back(ReceiveStep(8, 0x67));

	SessionReport report;
	NuxelRunEndSession(t, false, kSendTimeout, kRecvTimeout, kRebootTimeout,
	                   kNuxelEmptyTransferAfter, false, &report);

	checkEq(1, (long)t.emptyTransferTimeouts.size(), "empty after: exactly one empty transfer");
	if (!t.emptyTransferTimeouts.empty())
		checkEq(100, t.emptyTransferTimeouts[0], "empty after: bounded 100ms timeout");

	MockTransport t2;
	t2.receiveScript.push_back(ReceiveStep(8, 0x67));
	SessionReport report2;
	NuxelRunEndSession(t2, false, kSendTimeout, kRecvTimeout, kRebootTimeout,
	                   kNuxelEmptyTransferNone, false, &report2);
	checkEq(0, (long)t2.emptyTransferTimeouts.size(), "empty none: no empty transfers");

	MockTransport t3;
	t3.receiveScript.push_back(ReceiveStep(8, 0x67));
	SessionReport report3;
	NuxelRunEndSession(t3, false, kSendTimeout, kRecvTimeout, kRebootTimeout,
	                   kNuxelEmptyTransferBefore, false, &report3);
	checkEq(1, (long)t3.emptyTransferTimeouts.size(), "empty before: exactly one empty transfer");
}

// 13. A short control write must not be mistaken for success.
static void test_short_write(void)
{
	MockTransport t;
	t.sendResult = 512; // short write
	t.receiveScript.push_back(ReceiveStep(8, 0x67));

	SessionReport report;
	bool ok = NuxelRunEndSession(t, false, kSendTimeout, kRecvTimeout, kRebootTimeout,
	                             kNuxelEmptyTransferAfter, false, &report);

	check(!ok, "short write: returns false");
	checkEqStr("send_failed", report.ResultToken(), "short write: token");
}

// 14. No scripted reply at all (defaults to timeout) must never succeed.
static void test_no_script_never_succeeds(void)
{
	MockTransport t; // empty script -> every read times out

	SessionReport report;
	bool ok = NuxelRunEndSession(t, true, kSendTimeout, kRecvTimeout, kRebootTimeout,
	                             kNuxelEmptyTransferAfter, false, &report);

	check(!ok, "no script: returns false");
	check(!report.PositivelyAcknowledged(), "no script: never acknowledged");
}

int main(void)
{
	std::printf("Nuxel Heimdall session-handshake tests\n");
	std::printf("--------------------------------------\n");

	test_ok_no_reboot();
	test_ok_reboot();
	test_delayed_ack();
	test_missing_ack_timeout();
	test_usb_disconnect();
	test_malformed_short();
	test_malformed_length();
	test_rejected_command();
	test_send_failed();
	test_reboot_disconnect_unconfirmed();
	test_reboot_timeout();
	test_empty_transfer_flags();
	test_short_write();
	test_no_script_never_succeeds();

	std::printf("--------------------------------------\n");
	std::printf("checks: %d, failures: %d\n", checks, failures);

	if (failures == 0)
	{
		std::printf("RESULT: PASS\n");
		return (0);
	}

	std::printf("RESULT: FAIL\n");
	return (1);
}
