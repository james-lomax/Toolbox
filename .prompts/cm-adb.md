{{template("new-tool.md", tool_name="cm-adb")}}

`cm-adb` supports common functions to manipulate the Citymapper app through ADB.

Commands:

**clear-booking**

Usage: `cm-adb clear-booking`

Resets the booking state of the installed client over an ADB connection.

Uses ADB to do the following (in order):

- Kill com.citymapper.app.internal if running
- Kill com.citymapper.app.release if running
- Delete /data/data/com.citymapper.app.internal/no_backup/cm_active_booking_state.json
- Delete /data/data/com.citymapper.app.release/no_backup/cm_active_booking_state.json

Use e.g.:

```sh
adb shell run-as com.citymapper.app.internal rm /data/data/com.citymapper.app.internal/no_backup/cm_active_booking_state.json
```

To delete while running with this packages privileges.

Do all operations in order, even if they fail.
