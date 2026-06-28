# Changelog

## [0.9.0-beta.1] - 2026-06-22

### Added
- First public beta release of Kree AI!
- Intelligent Setup Installer (`setup.exe`) with WebView2 and VC++ detection.
- Background Voice Commands: Seamlessly talk to Kree without the UI interrupting your workflow.
- Customizable Push-to-Talk (PTT) silence timeout via the dashboard settings.
- First Run Diagnostics: Automatically generated health check log for beta testers.
- Safe Uninstaller: Optionally preserve your Kree configs and API keys when uninstalling.

### Fixed
- Fixed bug where the wakeword pipeline would pop up the dashboard inappropriately.
- Handled PyAudio device locking issues during build environments.

### Changed
- Shifted versioning scheme from 1.0.0 to 0.9.0-beta.1 to formally enter beta testing phase.
