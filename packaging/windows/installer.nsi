; WoW Stat Tracker - NSIS Installer Script
; BSD 3-Clause License

!include "MUI2.nsh"
!include "FileFunc.nsh"

; --------------------------------
; General
; --------------------------------

Name "WoW Stat Tracker"
OutFile "..\..\build-windows-Release\WoWStatTracker-${VERSION}-windows-x64-setup.exe"
InstallDir "$PROGRAMFILES64\WoWStatTracker"
InstallDirRegKey HKLM "Software\WoWStatTracker" "InstallDir"
RequestExecutionLevel admin
Unicode True

; Version info
!ifndef VERSION
  !define VERSION "1.2.0"
!endif
VIProductVersion "${VERSION}.0"
VIAddVersionKey "ProductName" "WoW Stat Tracker"
VIAddVersionKey "CompanyName" "WoW Stat Tracker"
VIAddVersionKey "FileDescription" "WoW Stat Tracker Installer"
VIAddVersionKey "FileVersion" "${VERSION}"
VIAddVersionKey "ProductVersion" "${VERSION}"
VIAddVersionKey "LegalCopyright" "BSD 3-Clause License"

; --------------------------------
; Interface Settings
; --------------------------------

!define MUI_ABORTWARNING
!define MUI_ICON "icon.ico"
!define MUI_UNICON "icon.ico"

; --------------------------------
; Pages
; --------------------------------

!insertmacro MUI_PAGE_WELCOME
!insertmacro MUI_PAGE_LICENSE "..\..\LICENSE"
!insertmacro MUI_PAGE_DIRECTORY
!insertmacro MUI_PAGE_INSTFILES
!insertmacro MUI_PAGE_FINISH

!insertmacro MUI_UNPAGE_CONFIRM
!insertmacro MUI_UNPAGE_INSTFILES

; --------------------------------
; Languages
; --------------------------------

!insertmacro MUI_LANGUAGE "English"

; --------------------------------
; Installer Sections
; --------------------------------

Section "WoW Stat Tracker" SecMain
  SectionIn RO  ; Required section

  SetOutPath "$INSTDIR"

  ; Install main executable
  File "..\..\build-windows-Release\Release\WoWStatTracker.exe"

  ; Install addon
  SetOutPath "$INSTDIR\WoWStatTracker_Addon"
  File /r "..\..\WoWStatTracker_Addon\*.*"

  ; Store installation folder
  WriteRegStr HKLM "Software\WoWStatTracker" "InstallDir" "$INSTDIR"

  ; Create uninstaller
  WriteUninstaller "$INSTDIR\Uninstall.exe"

  ; Add to Add/Remove Programs
  WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\WoWStatTracker" \
                   "DisplayName" "WoW Stat Tracker"
  WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\WoWStatTracker" \
                   "UninstallString" "$\"$INSTDIR\Uninstall.exe$\""
  WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\WoWStatTracker" \
                   "QuietUninstallString" "$\"$INSTDIR\Uninstall.exe$\" /S"
  WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\WoWStatTracker" \
                   "InstallLocation" "$INSTDIR"
  WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\WoWStatTracker" \
                   "DisplayIcon" "$INSTDIR\WoWStatTracker.exe"
  WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\WoWStatTracker" \
                   "Publisher" "WoW Stat Tracker"
  WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\WoWStatTracker" \
                   "DisplayVersion" "${VERSION}"
  WriteRegDWORD HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\WoWStatTracker" \
                     "NoModify" 1
  WriteRegDWORD HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\WoWStatTracker" \
                     "NoRepair" 1

  ; Get installed size
  ${GetSize} "$INSTDIR" "/S=0K" $0 $1 $2
  IntFmt $0 "0x%08X" $0
  WriteRegDWORD HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\WoWStatTracker" \
                     "EstimatedSize" "$0"

  ; Create Start Menu shortcuts (for all users since we're admin)
  SetShellVarContext all
  CreateDirectory "$SMPROGRAMS\WoW Stat Tracker"
  CreateShortcut "$SMPROGRAMS\WoW Stat Tracker\WoW Stat Tracker.lnk" "$INSTDIR\WoWStatTracker.exe" "" "$INSTDIR\WoWStatTracker.exe" 0
  CreateShortcut "$SMPROGRAMS\WoW Stat Tracker\Uninstall.lnk" "$INSTDIR\Uninstall.exe" "" "$INSTDIR\Uninstall.exe" 0

SectionEnd

Section "Desktop Shortcut" SecDesktop
  SetShellVarContext all
  CreateShortcut "$DESKTOP\WoW Stat Tracker.lnk" "$INSTDIR\WoWStatTracker.exe" "" "$INSTDIR\WoWStatTracker.exe" 0
SectionEnd

; --------------------------------
; Descriptions
; --------------------------------

LangString DESC_SecMain ${LANG_ENGLISH} "WoW Stat Tracker application and addon files."
LangString DESC_SecDesktop ${LANG_ENGLISH} "Create a desktop shortcut."

!insertmacro MUI_FUNCTION_DESCRIPTION_BEGIN
  !insertmacro MUI_DESCRIPTION_TEXT ${SecMain} $(DESC_SecMain)
  !insertmacro MUI_DESCRIPTION_TEXT ${SecDesktop} $(DESC_SecDesktop)
!insertmacro MUI_FUNCTION_DESCRIPTION_END

; --------------------------------
; Uninstaller Section
; --------------------------------

Section "Uninstall"

  ; Use all users context to match install
  SetShellVarContext all

  ; Remove files
  Delete "$INSTDIR\WoWStatTracker.exe"
  Delete "$INSTDIR\Uninstall.exe"

  ; Remove addon folder
  RMDir /r "$INSTDIR\WoWStatTracker_Addon"

  ; Remove install directory (only if empty)
  RMDir "$INSTDIR"

  ; Remove Start Menu shortcuts
  Delete "$SMPROGRAMS\WoW Stat Tracker\WoW Stat Tracker.lnk"
  Delete "$SMPROGRAMS\WoW Stat Tracker\Uninstall.lnk"
  RMDir "$SMPROGRAMS\WoW Stat Tracker"

  ; Remove desktop shortcut
  Delete "$DESKTOP\WoW Stat Tracker.lnk"

  ; Remove registry keys
  DeleteRegKey HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\WoWStatTracker"
  DeleteRegKey HKLM "Software\WoWStatTracker"

SectionEnd
