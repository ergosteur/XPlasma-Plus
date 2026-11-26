# Lock, login and boot screens

These are separate parts of the desktop. Select the desired features in Setup; unsupported components are disabled. Login/boot integration may require administrator authentication.

| Screen | When it appears | How to test |
| --- | --- | --- |
| Lock screen | Lock the running Plasma session, including lid-close locking when configured | Save work, then use KDE's Lock action; unlock with your normal credentials. |
| XP Welcome login screen | The SDDM greeter before starting a user session | Save work and log out; the system must be configured to use SDDM. |
| XP Welcome desktop splash | While the Plasma session starts after authentication | Log out and back in. |
| XP boot splash | Plymouth during system boot | Reboot after Setup and the boot-image rebuild finish successfully. |

## Lock screen

The lock screen is Plasma's own, with XP's Welcome screen (blue, with the XP banding) as its background when the wallpaper feature is installed; only its settings are changed, none of Plasma's files. The account picture is the one in **System Settings → Users**, where the XP account pictures are also offered.

Earlier releases (up to 1.0.4-beta.2) had an optional XP lock screen theme. It broke on Plasma 6.8 and was removed from this fork in 1.0.4-beta.3; upgrading or removing an installation that has it deletes it and Plasma's lock screen comes back.

A lock screen keeps your applications running. A full logout ends that session. On systems with other logged-in users, session switching can expose another session's lock screen; do not assume every password screen is SDDM. Include which action you used and whether other sessions exist when reporting a mismatch.

## Login screen

The XP Welcome login integration is for **SDDM**. A different display manager will not use an SDDM theme. Setup manages selected system components through the local administrator prompt. Avoid manually switching display managers solely to follow this tutorial; report the detected setup if the component is unavailable or does not apply.

## Boot screen

![1024×768 rendered boot-screen preview](https://raw.githubusercontent.com/andymenard/XPlasma-Plus/main/docs/screenshots/08-bootscreen-1024x768.png)

This image is a preview rendered from the bundled artwork and the Plymouth theme's layout, not a photograph of a boot. Real placement/display depends on firmware, graphics initialization and resolution. The blue blocks animate during boot.

An existing splash-enabled Plymouth setup using dracut or update-initramfs is required. Setup does not automatically alter bootloader arguments or force graphics drivers. Finish any administrator prompt and wait for successful boot-image generation before rebooting. If you see only text or a black screen, use [Troubleshooting](Troubleshooting.md); the repository has a narrowly scoped Intel/Kubuntu workaround, not a universal boot fix.
