export default {
  app: {
    name: '基金跟踪器',
    subtitle: 'Fund Tracker',
    version: 'v2.0.0'
  },
  nav: {
    home: '首页',
    screen: '基金筛选',
    compare: '基金对比',
    portfolio: '持仓管理',
    settings: '设置'
  },
  home: {
    title: '首页',
    subtitle: '实时追踪您的基金动态',
    stats: {
      up: '上涨',
      down: '下跌',
      watching: '关注',
      avgChange: '平均'
    },
    search: {
      placeholder: '搜索基金代码或名称',
      button: '搜索'
    },
    refresh: '刷新',
    export: '导出',
    exportSuccess: '导出成功',
    noDataToExport: '没有数据可导出',
    fundList: {
      title: '基金实时估值',
      code: '基金代码',
      name: '基金名称',
      nav: '估算净值',
      change: '涨跌幅',
      updateTime: '更新时间',
      status: '状态',
      actions: '操作',
      detail: '详情',
      chart: '图表',
      add: '添加',
      filter: {
        all: '全部',
        up: '上涨',
        down: '下跌'
      }
    },
    loading: '正在获取基金数据...',
    loadingSub: '首次加载可能需要 10-30 秒',
    noData: '暂无基金数据',
    loadDefault: '加载默认基金'
  },
  screen: {
    title: '基金筛选',
    subtitle: '筛选连续涨跌的基金',
    direction: '筛选方向',
    up: '连续上涨',
    down: '连续下跌',
    minDays: '最小天数',
    minPct: '最小幅度',
    startScreen: '开始筛选',
    days: '连续天数',
    totalPct: '累计涨跌幅',
    resultCount: '找到 {count} 只基金'
  },
  compare: {
    title: '基金对比',
    selectFunds: '选择基金',
    selectPlaceholder: '请选择要对比的基金',
    timeRange: '时间范围',
    startCompare: '开始对比',
    currentChange: '当前涨跌幅',
    emptyTip: '请选择2只或以上基金进行对比',
    showBenchmark: '显示基准',
    benchmarkIndex: '基准指数',
    benchmarkName: '指数名称'
  },
  portfolio: {
    title: '持仓管理',
    totalValue: '总市值',
    totalProfit: '总盈亏',
    profitRate: '收益率',
    addPosition: '添加持仓',
    myPositions: '我的持仓',
    positionCount: '共 {count} 只基金',
    holdShares: '持有份额',
    costPrice: '成本价',
    currentNav: '当前净值',
    currentValue: '当前市值',
    profitAmount: '盈亏金额',
    editPosition: '编辑持仓',
    deleteConfirm: '确定要删除这个持仓吗？',
    addSuccess: '已添加 {name}',
    addFailed: '添加失败'
  },
  error: {
    title: '出错了',
    retry: '重试',
    backHome: '返回首页',
    goBack: '返回上页',
    details: '错误详情',
    loadFailed: '加载失败',
    networkError: '网络连接失败，请检查网络',
    serverError: '服务器错误，请稍后重试',
    notFound: '页面未找到',
    notFoundDesc: '您访问的页面不存在或已被移除',
    forbidden: '没有权限访问'
  },
  about: {
    tagline: '智能基金追踪，让投资更简单',
    techStack: '技术栈',
    contact: '联系我们',
    copyright: '保留所有权利',
    features: {
      realtime: {
        title: '实时数据',
        desc: '获取最新的基金净值和涨跌幅数据'
      },
      alert: {
        title: '涨跌提醒',
        desc: '设置价格提醒，及时把握投资机会'
      },
      theme: {
        title: '深色模式',
        desc: '支持浅色/深色主题，保护您的眼睛'
      },
      export: {
        title: '数据导出',
        desc: '支持CSV/JSON格式导出基金数据'
      },
      i18n: {
        title: '多语言',
        desc: '支持中英文切换，满足国际化需求'
      }
    }
  },
  fund: {
    chartTitle: '基金走势',
    detailTitle: '基金详情',
    updateTime: '更新时间',
    previousNav: '昨日净值',
    accumulatedNav: '累计净值',
    dailyGrowth: '日增长率',
    historyTrend: '历史走势',
    addToWatchlist: '添加关注',
    alreadyInWatchlist: '该基金已在关注列表中',
    addSuccess: '已添加 {name}',
    addFailed: '添加失败'
  },
  settings: {
    appearance: '外观设置',
    language: '语言',
    theme: '主题模式',
    light: '浅色',
    dark: '深色',
    auto: '跟随系统',
    data: '数据设置',
    apiUrl: 'API地址',
    autoRefresh: '自动刷新',
    refreshInterval: '刷新间隔',
    about: '关于',
    version: '应用版本',
    saved: '设置已保存',
    reset: '设置已重置',
    themeChanged: '主题已切换'
  },
  common: {
    confirm: '确定',
    cancel: '取消',
    save: '保存',
    reset: '重置',
    delete: '删除',
    edit: '编辑',
    add: '添加',
    close: '关闭',
    success: '成功',
    error: '错误',
    warning: '警告',
    info: '提示',
    actions: '操作',
    month: '月',
    year: '年',
    week: '周',
    second: '秒'
  }
}
