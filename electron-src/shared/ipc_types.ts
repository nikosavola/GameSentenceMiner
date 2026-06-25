// Shared IPC payload types — types the trust boundary between renderer and main.
// Renderer-supplied payloads arrive untrusted, so every field is optional and
// handlers must still validate at runtime before use.

/** Payload for the `settings.saveSettings` IPC handler. */
export interface SaveSettingsPayload {
    autoUpdateGSMApp?: boolean;
    pullPreReleases?: boolean;
    autoUpdateElectron?: boolean;
    startConsoleMinimized?: boolean;
    customPythonPackage?: string;
    showYuzuTab?: boolean;
    windowTransparencyToolHotkey?: string;
    windowTransparencyTarget?: string;
    runWindowTransparencyToolOnStartup?: boolean;
    runOverlayOnStartup?: boolean;
    textCaptureWizardEnabled?: boolean;
    visibleTabs?: string[];
    statsEndpoint?: string;
    iconStyle?: string;
    theme?: string;
    locale?: string;
    consoleMode?: 'simple' | 'advanced';
    uiMode?: 'basic' | 'advanced';
    hasCompletedSetup?: boolean;
    setupWizardVersion?: number;
}
