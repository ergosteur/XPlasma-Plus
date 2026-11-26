# Icon fixes: credits and sources

Corrections applied on top of the two XP icon themes (XPlasma Primary and the
expanded layer); see `build.py` for what each one is and why, and `overlay.py`
for how they survive the desktop apply rewriting XPlasma Primary.

## Artwork

- `art/*.png` (except `view-list-tiles.png`) and `assets/*.png`: unmodified files
  from marchmountain's [Windows XP High Resolution Icon Pack](https://github.com/marchmountain/-Windows-XP-High-Resolution-Icon-Pack)
  (release 02, `Windows XP Icons/`), CC0-1.0. Byte-identical to:

  - `art/audio-cd.png`: `Audio CD.png`
  - `art/authorization-manager.png`: `Authorization Manager.png`
  - `art/cd-r.png`: `CD-R.png`
  - `art/cd-rom.png`: `CD-ROM.png`
  - `art/change-language.png`: `Change Language.png`
  - `art/disk-cleanup.png`: `Disk Cleanup.png`
  - `art/disk-management.png`: `Disk Management.png`
  - `art/dvd-rom.png`: `DVD-ROM.png`
  - `art/dvd.png`: `DVD.png`
  - `art/ir-file-transfer.png`: `IR File Transfer.png`
  - `art/jpg.png`: `JPG.png`
  - `art/memory-stick.png`: `Memory Stick.png`
  - `art/mp3-player.png`: `MP3 player.png`
  - `art/network-and-internet.png`: `Network and Internet.png`
  - `art/network-connections.png`: `Network Connections.png`
  - `art/printers-and-faxes.png`: `Printers and Faxes.png`
  - `art/recent-documents.png`: `Recent Documents.png`
  - `art/remote-assistance.png`: `Remote Assistance.png`
  - `art/remote-desktop.png`: `Remote Desktop.png`
  - `art/sd-card.png`: `SD Card.png`
  - `art/security-question.png`: `Security Question.png`
  - `assets/gif.png`: `GIF.png`
  - `assets/jpg.png`: `JPG.png`
  - `assets/workgroup.png`: `Workgroup.png`

- `art/view-list-tiles.png`: drawn by ergosteur (based on XP's Tiles view), contributed to this project.
- `svg/*.svg` (bell, globe-arrow, installer-box, msi) and `xp_marks.py` (the red X for off/disabled states): drawn for this project.

Not included: the compy-686 original used macOS's spinning beachball for `process-working`; that is Apple's
artwork and is not redistributable, so this version pins Breeze's own spinner instead.
