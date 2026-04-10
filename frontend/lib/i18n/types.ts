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
    /** 任务列表因会话不存在（404）已清空选中时的提示 */
    sessionMissingReset: string;
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
    /** 侧栏品牌区说明文案 */
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
    renameSessionMenu: string;
    deleteSessionMenu: string;
    renameSessionModalTitle: string;
    renameSessionPlaceholder: string;
    renameSessionSave: string;
    sessionMoreAria: string;
    collapseSidebarAria: string;
    expandSidebarAria: string;
    loadMoreSessions: string;
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
    usageTitle: string;
    usagePrompt: string;
    usageCompletion: string;
    usageTotal: string;
    usageCost: string;
    usageAvgTotal: string;
    usageAvgCost: string;
    usageSummaryTitle: string;
    usageScopeSession: string;
    usageScopeGlobal: string;
    usageSessionTitle: string;
    usageTaskCount: (n: number) => string;
    usageTaskCoverage: (withUsage: number, total: number) => string;
    usageSummaryLoading: string;
    usageSummaryError: string;
    usageSummaryEmpty: string;
    usageSessionLoading: string;
    usageSessionError: string;
    usageSessionEmpty: string;
    currentTaskCard: string;
    statusPrefix: string;
    latestTaskSession: string;
    recentTasks: string;
    sessionTasks: string;
    loadMoreTasks: string;
    backendUrl: string;
    seqLabel: string;
    collapseInspectorAria: string;
    expandInspectorAria: string;
    /** 轨迹卡片第二行：模型 / 子类 / token 占位 */
    traceMeta: {
      model: string;
      stepKind: string;
      tokens: string;
      toolLine: (name: string, status: string) => string;
      ragLine: (chunkCount: number, knowledgeBaseId?: string) => string;
    };
    /** 轨迹：列表时间线 vs 流程图 */
    traceViewList: string;
    traceViewFlow: string;
    /** 流程图节点：三大类标签与折叠内容 */
    traceFlow: {
      kindThought: string;
      kindAction: string;
      kindObservation: string;
      kindTool: string;
      kindRag: string;
      kindOther: string;
      contentDetails: string;
      contentEmpty: string;
    };
    /** 上下文：Memory / Chroma */
    memory: {
      kicker: string;
      title: string;
      lead: string;
      collectionLabel: string;
      chromaConnected: string;
      chromaDisconnected: string;
      docCount: (n: number) => string;
      collectionExists: string;
      collectionMissing: string;
      statusLoading: string;
      pickSession: string;
      debugKicker: string;
      addPlaceholder: string;
      addButton: string;
      addEmpty: string;
      queryInputEmpty: string;
      addSuccess: (n: number) => string;
      queryPlaceholder: string;
      queryButton: string;
      queryEmpty: string;
      queryHits: (n: number) => string;
      distanceLabel: string;
      metadataPlaceholder: string;
      metadataInvalid: string;
      hitMetadataLabel: string;
    };
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
