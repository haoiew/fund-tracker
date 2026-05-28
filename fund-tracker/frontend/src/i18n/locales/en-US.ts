export default {
  app: {
    name: 'Fund Tracker',
    subtitle: 'Track Your Funds',
    version: 'v2.0.0'
  },
  nav: {
    home: 'Home',
    screen: 'Screen',
    compare: 'Compare',
    portfolio: 'Portfolio',
    settings: 'Settings'
  },
  home: {
    title: 'Home',
    subtitle: 'Track your fund dynamics in real-time',
    stats: {
      up: 'Up',
      down: 'Down',
      watching: 'Watching',
      avgChange: 'Avg'
    },
    search: {
      placeholder: 'Search fund code or name',
      button: 'Search'
    },
    refresh: 'Refresh',
    export: 'Export',
    exportSuccess: 'Export successful',
    noDataToExport: 'No data to export',
    fundList: {
      title: 'Fund Real-time Valuation',
      code: 'Code',
      name: 'Name',
      nav: 'NAV',
      change: 'Change',
      updateTime: 'Update Time',
      status: 'Status',
      actions: 'Actions',
      detail: 'Detail',
      chart: 'Chart',
      add: 'Add',
      filter: {
        all: 'All',
        up: 'Up',
        down: 'Down'
      }
    },
    loading: 'Loading fund data...',
    loadingSub: 'First load may take 10-30 seconds',
    noData: 'No fund data',
    loadDefault: 'Load Default Funds'
  },
  screen: {
    title: 'Screen',
    subtitle: 'Screen funds with consecutive rise or fall',
    direction: 'Direction',
    up: 'Consecutive Up',
    down: 'Consecutive Down',
    minDays: 'Min Days',
    minPct: 'Min Percentage',
    startScreen: 'Start Screening',
    days: 'Days',
    totalPct: 'Total Change',
    resultCount: 'Found {count} funds'
  },
  compare: {
    title: 'Compare',
    selectFunds: 'Select Funds',
    selectPlaceholder: 'Select funds to compare',
    timeRange: 'Time Range',
    startCompare: 'Compare',
    currentChange: 'Current Change',
    emptyTip: 'Please select 2 or more funds to compare'
  },
  portfolio: {
    title: 'Portfolio',
    totalValue: 'Total Value',
    totalProfit: 'Total Profit',
    profitRate: 'Return Rate',
    addPosition: 'Add Position',
    myPositions: 'My Positions',
    positionCount: '{count} funds',
    holdShares: 'Hold Shares',
    costPrice: 'Cost Price',
    currentNav: 'Current NAV',
    currentValue: 'Current Value',
    profitAmount: 'Profit/Loss',
    editPosition: 'Edit Position',
    deleteConfirm: 'Are you sure to delete this position?',
    addSuccess: 'Added {name}',
    addFailed: 'Add failed'
  },
  error: {
    title: 'Something went wrong',
    retry: 'Retry',
    backHome: 'Back to Home',
    goBack: 'Go Back',
    details: 'Error Details',
    loadFailed: 'Failed to load',
    networkError: 'Network error, please check your connection',
    serverError: 'Server error, please try again later',
    notFound: 'Page not found',
    notFoundDesc: 'The page you are looking for does not exist or has been removed',
    forbidden: 'Access denied'
  },
  about: {
    tagline: 'Smart fund tracking, making investing easier',
    techStack: 'Tech Stack',
    contact: 'Contact Us',
    copyright: 'All rights reserved',
    features: {
      realtime: {
        title: 'Real-time Data',
        desc: 'Get the latest fund NAV and change data'
      },
      alert: {
        title: 'Price Alerts',
        desc: 'Set price reminders for investment opportunities'
      },
      theme: {
        title: 'Dark Mode',
        desc: 'Support light/dark themes to protect your eyes'
      },
      export: {
        title: 'Data Export',
        desc: 'Export fund data in CSV/JSON format'
      },
      i18n: {
        title: 'Multi-language',
        desc: 'Support Chinese/English for international users'
      }
    }
  },
  fund: {
    chartTitle: 'Fund Trend',
    detailTitle: 'Fund Detail',
    updateTime: 'Update Time',
    previousNav: 'Previous NAV',
    accumulatedNav: 'Accumulated NAV',
    dailyGrowth: 'Daily Growth',
    historyTrend: 'History Trend',
    addToWatchlist: 'Add to Watchlist',
    alreadyInWatchlist: 'This fund is already in the watchlist',
    addSuccess: 'Added {name}',
    addFailed: 'Add failed'
  },
  settings: {
    appearance: 'Appearance',
    language: 'Language',
    theme: 'Theme',
    light: 'Light',
    dark: 'Dark',
    auto: 'Auto',
    data: 'Data Settings',
    apiUrl: 'API URL',
    autoRefresh: 'Auto Refresh',
    refreshInterval: 'Refresh Interval',
    about: 'About',
    version: 'Version',
    saved: 'Settings saved',
    reset: 'Settings reset',
    themeChanged: 'Theme changed'
  },
  common: {
    confirm: 'Confirm',
    cancel: 'Cancel',
    save: 'Save',
    reset: 'Reset',
    delete: 'Delete',
    edit: 'Edit',
    add: 'Add',
    close: 'Close',
    success: 'Success',
    error: 'Error',
    warning: 'Warning',
    info: 'Info',
    month: 'M',
    year: 'Y',
    week: 'W',
    second: 's'
  }
}
