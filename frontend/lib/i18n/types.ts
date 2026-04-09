export type Locale = "zh" | "en";

export type Messages = {
  errors: {
    networkBanner: string;
    networkHint: string;
    unknownBanner: string;
    notFound: string;
    auth: string;
    server: string;
    checkBackend: string;
    requestFailed: string;
  };
  workbench: {
    selectSessionForHistory: string;
    sessionEmpty: string;
    loadedHistory: string;
    loadingMessages: string;
    noSessions: string;
    streamFailedBadge: string;
    liveRegionDone: string;
    liveRegionError: string;
    composerEnterSend: string;
    composerGenerating: string;
    /** 悬停在输入框上提示 ⌘K / Ctrl+K */
    cmdKHint: string;
    traceExpandAll: string;
    traceCollapse: string;
    traceHidden: (n: number) => string;
    phaseDone: string;
    phaseError: string;
    phaseReplay: string;
    phaseRunning: string;
    phaseIdle: string;
    sessionFallback: (shortId: string) => string;
    taskFallback: (shortId: string) => string;
    hintRowNarrow: string;
  };
  roles: {
    user: string;
    assistantShort: string;
    assistantName: string;
  };
  chat: {
    kicker: string;
    newChatTitle: string;
    updatedAt: (ts: string) => string;
    autoCreateHint: string;
    sessionList: string;
    traceAndContext: string;
    modeLabel: string;
    ready: string;
    generating: string;
    closeBanner: string;
    relatedTask: (shortId: string) => string;
    streamOutputting: string;
    streamInterrupted: string;
    streamLatest: string;
    scrollToBottom: string;
    scrollToBottomAria: string;
    sessionEmptyTitle: string;
    sessionEmptyLead: string;
    onboardingTitle: string;
    onboardingLead: string;
  };
  composer: {
    placeholder: string;
    inputAria: string;
    retry: string;
    send: string;
    sending: string;
  };
  sidebar: {
    ariaLabel: string;
    brandTitle: string;
    brandLead: string;
    sessionsHeading: string;
    newSession: string;
    creating: string;
    loading: string;
    empty: string;
    /** 左下角设置按钮 */
    settingsButton: string;
    settingsMenuLabel: string;
    menuTheme: string;
    /** 强调色 / 主色 */
    menuAccent: string;
    menuLanguage: string;
    menuModel: string;
    subviewBack: string;
    themeCurrentDark: string;
    themeCurrentLight: string;
    langCurrentZh: string;
    langCurrentEn: string;
    deleteSessionTitle: string;
    deleteSessionConfirm: string;
    deleteSessionOk: string;
    deleteSessionCancel: string;
    deleteSessionAria: string;
    /** 主题色下方色盘 / 自定义 */
    accentCustomColor: string;
  };
  inspector: {
    ariaShell: string;
    ariaTablist: string;
    tabTrace: string;
    tabContext: string;
    traceKicker: string;
    timelineTitle: string;
    stepsCount: (n: number) => string;
    stepsNone: string;
    replayTrace: string;
    loadDelta: string;
    stepEmpty: string;
    traceEmpty: string;
    contextKicker: string;
    summaryTitle: string;
    currentPhase: string;
    currentTask: string;
    traceCursor: string;
    session: string;
    currentTaskCard: string;
    statusPrefix: string;
    latestTaskSession: string;
    recentTasks: string;
    backendUrl: string;
    seqLabel: string;
  };
  settings: {
    title: string;
    lead: string;
    close: string;
    loading: string;
    fieldMode: string;
    fieldProvider: string;
    fieldModel: string;
    fieldBaseUrl: string;
    fieldApiKey: string;
    optionalPlaceholder: string;
    save: string;
    saving: string;
    apiKeyConfiguredKeep: string;
    apiKeyOptionalMock: string;
    metaProvider: string;
    metaModel: string;
    metaApiKey: string;
    metaConfigured: string;
    metaNotConfigured: string;
    metaSqlite: string;
    appearanceTitle: string;
    themeLabel: string;
    themeDark: string;
    themeLight: string;
    languageLabel: string;
    languageZh: string;
    languageEn: string;
    /** 弹窗内副标题 */
    modalSubtitle: string;
  };
  a11y: {
    closeSessionDrawer: string;
    closeInspectorDrawer: string;
  };
};
