# Toast Notification System

This document describes how to use the toast notification system that has been implemented throughout the application.

## Overview

The toast notification system provides a consistent and attractive way to display alerts, notifications, and messages to users. It replaces the traditional alert dialogs and message boxes with modern toast notifications that appear in the top-right corner of the screen by default.

## How to Use

### In Templates

To show a toast notification from a template, you can use the `showToast` function:

```javascript
showToast("Your message here", "Title (optional)", "type");
```

The type parameter can be one of:
- `"success"` - Green notification for successful operations
- `"error"` - Red notification for errors
- `"warning"` - Yellow notification for warnings
- `"info"` - Blue notification for informational messages (default)

### Examples

#### Success message:
```javascript
showToast("Data saved successfully", "Success", "success");
```

#### Error message:
```javascript
showToast("Failed to save data", "Error", "error");
```

#### Warning message:
```javascript
showToast("Please complete all required fields", "Warning", "warning");
```

#### Info message:
```javascript
showToast("New updates are available", "Information", "info");
```

### For Django Messages

Django messages are automatically converted to toast notifications. The system maps Django message tags to the appropriate toast type:
- `success` → Success toast
- `error`/`danger` → Error toast
- `warning` → Warning toast
- Other tags → Info toast

### Using Data Attributes (For Django Template Variables)

If you need to use Django template variables in JavaScript without causing linter errors, you can use data attributes:

```html
<div id="notification-data" 
     style="display: none;"
     data-show="true"
     data-message="{{ your_message }}"
     data-title="{{ your_title }}"
     data-type="{{ message_type }}">
</div>

<script>
$(document).ready(function() {
    var notification = $("#notification-data");
    if (notification.length > 0 && notification.data('show')) {
        showToast(
            notification.data('message'),
            notification.data('title'),
            notification.data('type')
        );
    }
});
</script>
```

## Configuration

The toast notification system is configured with the following default settings:

- Close button: Yes
- Progress bar: Yes
- Position: Top-right
- Duration: 5 seconds
- Transition effects: Fade

If you need to modify these settings, you can edit the `toastr.options` object in the base.html file.

## Dependencies

The toast notification system uses the Toastr library, which is already included in the project's static files. 