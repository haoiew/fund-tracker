// Test-only API boundary; never imported by the application build.
export default {
  getFundList: (...args) => globalThis.loadingTestApi.getFundList(...args),
  getAll: (...args) => globalThis.loadingTestApi.getAll(...args),
  getRealtimeBatch: (...args) => globalThis.loadingTestApi.getRealtimeBatch(...args)
}
