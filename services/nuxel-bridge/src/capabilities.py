#!/usr/bin/env python3
"""
Nuxel Bridge - Capability Model (Extended)

Defines the capability-based permission system for PWA access to phone hardware.
Extended with new capabilities: network, storage, background, display, USB, BT.

Capability Categories:
    call:*          - Telephony operations
    sms:*           - SMS messaging
    contacts:*      - Contact management
    location:*      - GPS/location access
    camera:*        - Camera access
    notifications:* - Notification access
    phone:*         - Phone status monitoring
    network:*       - Network access (NEW)
    storage:*       - Persistent storage (NEW)
    background:*    - Background execution (NEW)
    display:*       - Display capture (NEW)
    usb:*           - USB device access (NEW)
    bluetooth:*     - Bluetooth access (NEW)
"""

from enum import Enum


class Capability(str, Enum):
    """All defined capabilities for the Nuxel Bridge."""
    
    # Telephony
    CALL_INITIATE = 'call:initiate'
    CALL_END = 'call:end'
    CALL_STATUS = 'call:status'
    
    # SMS
    SMS_SEND = 'sms:send'
    SMS_RECEIVE = 'sms:receive'
    
    # Contacts
    CONTACTS_READ = 'contacts:read'
    CONTACTS_WRITE = 'contacts:write'
    
    # Location
    LOCATION_READ = 'location:read'
    
    # Camera
    CAMERA_CAPTURE = 'camera:capture'
    CAMERA_PREVIEW = 'camera:preview'
    
    # Notifications
    NOTIFICATIONS_SEND = 'notifications:send'
    NOTIFICATIONS_RECEIVE = 'notifications:receive'
    
    # Status
    PHONE_STATUS = 'phone:status'
    
    # === Extended Capabilities (NEW) ===
    
    # Network
    NETWORK_OUTBOUND = 'network:outbound'
    NETWORK_INBOUND = 'network:inbound'
    
    # Storage
    STORAGE_PERSISTENT = 'storage:persistent'
    
    # Background
    BACKGROUND_EXECUTION = 'background:execution'
    
    # Display
    DISPLAY_SCREENSHOT = 'display:screenshot'
    DISPLAY_SCREENCAST = 'display:screencast'
    
    # USB
    USB_ACCESS = 'usb:access'
    
    # Bluetooth
    BLUETOOTH_SCAN = 'bluetooth:scan'
    BLUETOOTH_CONNECT = 'bluetooth:connect'


class CapabilityState(Enum):
    """State of a capability grant."""
    PENDING = 'pending'
    GRANTED = 'granted'
    DENIED = 'denied'
    REVOKED = 'revoked'


# Capability metadata with descriptions, risk levels, portal types
CAPABILITY_INFO = {
    # Core phone capabilities
    Capability.CALL_INITIATE: {
        'name': 'Initiate Calls',
        'description': 'Allows the app to place phone calls',
        'risk': 'high',
        'persistent': False,
        'prompt': 'Allow this app to make phone calls?',
        'portal_type': 'call',
    },
    Capability.CALL_END: {
        'name': 'End Calls',
        'description': 'Allows the app to end active phone calls',
        'risk': 'medium',
        'persistent': False,
        'prompt': 'Allow this app to end calls?',
        'portal_type': 'call',
    },
    Capability.CALL_STATUS: {
        'name': 'Call Status',
        'description': 'Allows the app to monitor call status',
        'risk': 'low',
        'persistent': True,
        'prompt': 'Allow this app to see call status?',
        'portal_type': 'call',
    },
    Capability.SMS_SEND: {
        'name': 'Send SMS',
        'description': 'Allows the app to send SMS messages',
        'risk': 'high',
        'persistent': False,
        'prompt': 'Allow this app to send SMS messages?',
        'portal_type': 'sms',
    },
    Capability.SMS_RECEIVE: {
        'name': 'Receive SMS',
        'description': 'Allows the app to read incoming SMS messages',
        'risk': 'high',
        'persistent': True,
        'prompt': 'Allow this app to read SMS messages?',
        'portal_type': 'sms',
    },
    Capability.CONTACTS_READ: {
        'name': 'Read Contacts',
        'description': 'Allows the app to read your contacts',
        'risk': 'medium',
        'persistent': True,
        'prompt': 'Allow this app to access your contacts?',
        'portal_type': 'contacts',
    },
    Capability.CONTACTS_WRITE: {
        'name': 'Modify Contacts',
        'description': 'Allows the app to create and edit contacts',
        'risk': 'medium',
        'persistent': True,
        'prompt': 'Allow this app to modify your contacts?',
        'portal_type': 'contacts',
    },
    Capability.LOCATION_READ: {
        'name': 'Location',
        'description': 'Allows the app to access your GPS location',
        'risk': 'high',
        'persistent': False,
        'prompt': 'Allow this app to access your location?',
        'portal_type': 'location',
    },
    Capability.CAMERA_CAPTURE: {
        'name': 'Camera Capture',
        'description': 'Allows the app to take photos and record video',
        'risk': 'high',
        'persistent': False,
        'prompt': 'Allow this app to use the camera?',
        'portal_type': 'camera',
    },
    Capability.CAMERA_PREVIEW: {
        'name': 'Camera Preview',
        'description': 'Allows the app to show camera preview without capturing',
        'risk': 'medium',
        'persistent': False,
        'prompt': 'Allow this app to access the camera preview?',
        'portal_type': 'camera',
    },
    Capability.NOTIFICATIONS_SEND: {
        'name': 'Send Notifications',
        'description': 'Allows the app to send notifications to the system',
        'risk': 'low',
        'persistent': True,
        'prompt': 'Allow this app to send notifications?',
        'portal_type': None,  # No portal needed
    },
    Capability.NOTIFICATIONS_RECEIVE: {
        'name': 'Receive Notifications',
        'description': 'Allows the app to receive system notifications',
        'risk': 'low',
        'persistent': True,
        'prompt': 'Allow this app to receive notifications?',
        'portal_type': None,
    },
    Capability.PHONE_STATUS: {
        'name': 'Phone Status',
        'description': 'Allows the app to see phone status (signal, battery, network)',
        'risk': 'low',
        'persistent': True,
        'prompt': 'Allow this app to see phone status?',
        'portal_type': 'phone_status',
    },
    
    # === Extended capabilities ===
    
    Capability.NETWORK_OUTBOUND: {
        'name': 'Network Access',
        'description': 'Allows the app to access the internet (outbound connections)',
        'risk': 'medium',
        'persistent': True,
        'prompt': 'Allow this app to access the internet?',
        'portal_type': 'network',
        'sandbox_flag': 'network',
    },
    Capability.NETWORK_INBOUND: {
        'name': 'Inbound Connections',
        'description': 'Allows the app to accept incoming network connections (runs a server)',
        'risk': 'high',
        'persistent': True,
        'prompt': 'Allow this app to accept incoming connections?',
        'portal_type': 'network',
        'sandbox_flag': 'network',
    },
    Capability.STORAGE_PERSISTENT: {
        'name': 'Persistent Storage',
        'description': 'Allows the app to store data persistently on your device',
        'risk': 'low',
        'persistent': True,
        'prompt': 'Allow this app to store data on your device?',
        'portal_type': None,
    },
    Capability.BACKGROUND_EXECUTION: {
        'name': 'Background Execution',
        'description': 'Allows the app to run in the background after you switch away',
        'risk': 'medium',
        'persistent': True,
        'prompt': 'Allow this app to run in the background?',
        'portal_type': 'background',
        'sandbox_flag': 'background',
    },
    Capability.DISPLAY_SCREENSHOT: {
        'name': 'Screen Capture',
        'description': 'Allows the app to capture the screen as an image',
        'risk': 'high',
        'persistent': False,
        'prompt': 'Allow this app to capture your screen?',
        'portal_type': 'screenshot',
    },
    Capability.DISPLAY_SCREENCAST: {
        'name': 'Screen Recording',
        'description': 'Allows the app to record the screen as video',
        'risk': 'high',
        'persistent': False,
        'prompt': 'Allow this app to record your screen?',
        'portal_type': 'screencast',
    },
    Capability.USB_ACCESS: {
        'name': 'USB Access',
        'description': 'Allows the app to access USB devices',
        'risk': 'high',
        'persistent': True,
        'prompt': 'Allow this app to access USB devices?',
        'portal_type': 'usb',
        'sandbox_flag': 'devices',
    },
    Capability.BLUETOOTH_SCAN: {
        'name': 'Bluetooth Scan',
        'description': 'Allows the app to scan for nearby Bluetooth devices',
        'risk': 'low',
        'persistent': True,
        'prompt': 'Allow this app to scan for Bluetooth devices?',
        'portal_type': 'bluetooth',
    },
    Capability.BLUETOOTH_CONNECT: {
        'name': 'Bluetooth Connect',
        'description': 'Allows the app to connect to Bluetooth devices',
        'risk': 'medium',
        'persistent': True,
        'prompt': 'Allow this app to connect to Bluetooth devices?',
        'portal_type': 'bluetooth',
    },
}


# Extended capability hierarchy group
EXTENDED_CAPABILITY_HIERARCHY = {
    'network': {
        'name': 'Network',
        'icon': 'network-wireless',
        'description': 'Internet and local network access',
        'capabilities': ['network:outbound', 'network:inbound'],
    },
    'storage': {
        'name': 'Storage',
        'icon': 'drive-harddisk',
        'description': 'Persistent data storage',
        'capabilities': ['storage:persistent'],
    },
    'background': {
        'name': 'Background',
        'icon': 'media-playback-paused',
        'description': 'Background execution after switch away',
        'capabilities': ['background:execution'],
    },
    'display': {
        'name': 'Display Capture',
        'icon': 'video-display',
        'description': 'Screen capture and recording',
        'capabilities': ['display:screenshot', 'display:screencast'],
    },
    'usb': {
        'name': 'USB',
        'icon': 'media-removable',
        'description': 'USB device access',
        'capabilities': ['usb:access'],
    },
    'bluetooth': {
        'name': 'Bluetooth',
        'icon': 'bluetooth',
        'description': 'Bluetooth device scanning and connections',
        'capabilities': ['bluetooth:scan', 'bluetooth:connect'],
    },
}


def get_capability_hierarchy():
    """Return the hierarchical grouping of all capabilities."""
    hierarchy = {
        'call': {
            'name': 'Phone Calls',
            'icon': 'phone',
            'capabilities': ['call:initiate', 'call:end', 'call:status'],
        },
        'sms': {
            'name': 'Messaging',
            'icon': 'message',
            'capabilities': ['sms:send', 'sms:receive'],
        },
        'contacts': {
            'name': 'Contacts',
            'icon': 'contacts',
            'capabilities': ['contacts:read', 'contacts:write'],
        },
        'location': {
            'name': 'Location',
            'icon': 'location',
            'capabilities': ['location:read'],
        },
        'camera': {
            'name': 'Camera',
            'icon': 'camera',
            'capabilities': ['camera:capture', 'camera:preview'],
        },
        'notifications': {
            'name': 'Notifications',
            'icon': 'notification',
            'capabilities': ['notifications:send', 'notifications:receive'],
        },
        'phone': {
            'name': 'Phone Status',
            'icon': 'info',
            'capabilities': ['phone:status'],
        },
    }
    # Merge extended hierarchy
    hierarchy.update(EXTENDED_CAPABILITY_HIERARCHY)
    return hierarchy


def get_required_capabilities(app_type):
    """Return the default required capabilities for a given app type."""
    defaults = {
        'dialer': ['call:initiate', 'call:end', 'call:status', 'contacts:read'],
        'messages': ['sms:send', 'sms:receive', 'contacts:read'],
        'contacts': ['contacts:read', 'contacts:write'],
        'home': ['phone:status', 'notifications:receive', 'storage:persistent'],
        'mail': ['notifications:send', 'notifications:receive', 'network:outbound'],
        'calendar': ['notifications:send', 'storage:persistent'],
        'notes': ['storage:persistent'],
        'files': ['storage:persistent'],
        'camera': ['camera:capture', 'camera:preview', 'storage:persistent'],
        'browser': ['network:outbound', 'storage:persistent'],
        'navigation': ['location:read', 'network:outbound'],
    }
    return defaults.get(app_type, [])


def get_capability_risk(capability):
    """Return the risk level of a capability."""
    info = CAPABILITY_INFO.get(capability, {})
    return info.get('risk', 'medium')


def get_sandbox_flags(capabilities):
    """Convert a list of capabilities to sandbox flag bitmask."""
    flags = 0
    flag_map = {
        'network:outbound': 1,  # NUXXEL_SANDBOX_NETWORK
        'network:inbound': 1,
        'camera:capture': 16,    # NUXXEL_SANDBOX_CAMERA
        'camera:preview': 16,
        'background:execution': 32,  # NUXXEL_SANDBOX_BACKGROUND
        'usb:access': 4,         # NUXXEL_SANDBOX_DEVICES
    }
    for cap in capabilities:
        if cap in flag_map:
            flags |= flag_map[cap]
    return flags
