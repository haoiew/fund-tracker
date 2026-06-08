<template>
  <div class="portfolio-view workbench-page">
    <section class="page-toolbar">
      <div class="page-toolbar__main">
        <span class="page-toolbar__icon">
          <el-icon><Wallet /></el-icon>
        </span>
        <div class="page-toolbar__copy">
          <h2 class="page-toolbar__title">持仓管理工作台</h2>
          <p class="page-toolbar__meta">{{ portfolioStore.itemCount }} 条持仓 · 总市值 ¥{{ formatNumber(portfolioStore.totalValue) }} · {{ selectedItems.length > 0 ? `已选 ${selectedItems.length} 条` : '组合维护' }}</p>
        </div>
      </div>
      <div class="page-toolbar__actions">
        <el-button type="primary" :icon="Plus" @click="showAddDialog = true">{{ $t('portfolio.addPosition') }}</el-button>
        <el-button :icon="Upload" @click="showImportDialog = true">导入持仓</el-button>
      </div>
    </section>

    <section class="metric-grid portfolio-metrics">
      <div class="metric-card">
        <div class="metric-icon is-primary">
          <el-icon><Wallet /></el-icon>
        </div>
        <div class="metric-body">
          <div class="metric-value">¥{{ formatNumber(portfolioStore.totalValue) }}</div>
          <div class="metric-label">{{ $t('portfolio.totalValue') }}</div>
        </div>
      </div>

      <div class="metric-card">
        <div class="metric-icon" :class="portfolioStore.profitPositive ? 'is-up' : 'is-down'">
          <el-icon><TrendCharts /></el-icon>
        </div>
        <div class="metric-body">
          <div class="metric-value" :class="portfolioStore.profitPositive ? 'text-success' : 'text-danger'">
            {{ portfolioStore.profitPositive ? '+' : '' }}¥{{ formatNumber(portfolioStore.totalProfit) }}
          </div>
          <div class="metric-label">{{ $t('portfolio.totalProfit') }}</div>
        </div>
      </div>

      <div class="metric-card">
        <div class="metric-icon" :class="portfolioStore.profitPositive ? 'is-up' : 'is-down'">
          <el-icon><Percentage /></el-icon>
        </div>
        <div class="metric-body">
          <div class="metric-value" :class="portfolioStore.profitPositive ? 'text-success' : 'text-danger'">
            {{ portfolioStore.profitPositive ? '+' : '' }}{{ portfolioStore.totalProfitPct.toFixed(2) }}%
          </div>
          <div class="metric-label">{{ $t('portfolio.profitRate') }}</div>
        </div>
      </div>

      <div class="metric-card">
        <div class="metric-icon">
          <el-icon><Wallet /></el-icon>
        </div>
        <div class="metric-body">
          <div class="metric-value">{{ portfolioStore.itemCount }}</div>
          <div class="metric-label">{{ $t('portfolio.myPositions') }}</div>
        </div>
      </div>
    </section>

    <section class="portfolio-toolbar workbench-panel surface-panel">
      <div class="toolbar-row">
        <div>
          <div class="workbench-panel__title">组合维护</div>
          <div class="workbench-panel__meta">
            {{ selectedItems.length > 0 ? `已选择 ${selectedItems.length} 条持仓` : '刷新估值、清理缓存或补全导入后的基金信息' }}
          </div>
        </div>
        <div class="inline-actions">
          <el-button :icon="Refresh" :loading="portfolioStore.loading" @click="refreshData">{{ $t('home.refresh') }}</el-button>
          <el-button
            v-if="pendingItems.length > 0"
            type="warning"
            :icon="Loading"
            :loading="importLoading"
            @click="completeAllPending"
          >
            补全数据 ({{ pendingItems.length }})
          </el-button>
          <el-button
            v-if="selectedItems.length > 0"
            type="danger"
            :icon="Delete"
            @click="batchDelete"
          >
            批量删除 ({{ selectedItems.length }})
          </el-button>
          <el-button :icon="Delete" @click="clearCache" type="danger" plain>清除缓存</el-button>
        </div>
      </div>
    </section>

    <section class="portfolio-list workbench-panel surface-panel">
      <div class="workbench-panel__header">
        <div>
          <div class="workbench-panel__title">{{ $t('portfolio.myPositions') }}</div>
          <div class="workbench-panel__meta">{{ $t('portfolio.positionCount', { count: portfolioStore.itemCount }) }}</div>
        </div>
      </div>

      <div v-if="portfolioStore.error && portfolioStore.items.length === 0 && !portfolioStore.loading" class="error-note">
        <div>
          <strong>数据加载错误:</strong>
          <span>{{ portfolioStore.error }}</span>
        </div>
        <el-button type="primary" size="small" @click="refreshData">重新加载</el-button>
      </div>

      <div v-if="portfolioStore.items.length > 0" class="table-note">
        共 {{ portfolioStore.items.length }} 条数据
      </div>

      <el-table
        v-if="portfolioStore.items.length > 0 || portfolioStore.loading"
        ref="portfolioTableRef"
        :data="portfolioStore.items"
        stripe
        class="portfolio-table"
        max-height="640"
        v-loading="portfolioStore.loading"
        :empty-text="portfolioStore.loading ? '加载中...' : '暂无数据'"
        border
        @selection-change="handleSelectionChange"
      >
        <el-table-column type="selection" width="55" align="center" />
        <el-table-column prop="fund_code" :label="$t('home.fundList.code')" min-width="120" sortable>
          <template #default="{ row }">
            <div v-if="row.fund_code" class="fund-code-cell">
              <el-tag size="small" type="primary">{{ row.fund_code }}</el-tag>
            </div>
            <div v-else class="fund-code-loading">
              <el-icon class="is-loading"><Loading /></el-icon>
              <span class="loading-text">加载中...</span>
            </div>
          </template>
        </el-table-column>
        <el-table-column prop="fund_name" :label="$t('home.fundList.name')" min-width="180" show-overflow-tooltip sortable />
        <el-table-column prop="hold_shares" :label="$t('portfolio.holdShares')" min-width="100" align="right" sortable>
          <template #default="{ row }">
            {{ formatNumber(row.hold_shares || 0) }}
          </template>
        </el-table-column>
        <el-table-column prop="cost_nav" :label="$t('portfolio.costPrice')" min-width="90" align="right" sortable>
          <template #default="{ row }">
            ¥{{ Number(row.cost_nav || 0).toFixed(4) }}
          </template>
        </el-table-column>
        <el-table-column prop="current_nav" :label="$t('portfolio.currentNav')" min-width="90" align="right" sortable>
          <template #default="{ row }">
            <span :class="getProfitClass(row)">
              ¥{{ Number(row.current_nav || row.cost_nav || 0).toFixed(4) }}
            </span>
          </template>
        </el-table-column>
        <el-table-column prop="current_value" :label="$t('portfolio.currentValue')" min-width="110" align="right" sortable>
          <template #default="{ row }">
            ¥{{ formatNumber(row.current_value || row.cost_amount || 0) }}
          </template>
        </el-table-column>
        <el-table-column prop="profit_amount" :label="$t('portfolio.profitAmount')" min-width="110" align="right" sortable>
          <template #default="{ row }">
            <span :class="(row.profit_amount || 0) >= 0 ? 'text-success' : 'text-danger'">
              {{ (row.profit_amount || 0) >= 0 ? '+' : '' }}¥{{ formatNumber(row.profit_amount || 0) }}
            </span>
          </template>
        </el-table-column>
        <el-table-column prop="profit_rate" :label="$t('portfolio.profitRate')" min-width="90" align="right" sortable>
          <template #default="{ row }">
            <span :class="(row.profit_rate || 0) >= 0 ? 'text-success' : 'text-danger'">
              {{ (row.profit_rate || 0) >= 0 ? '+' : '' }}{{ (row.profit_rate || 0).toFixed(2) }}%
            </span>
          </template>
        </el-table-column>
        <el-table-column label="操作" min-width="130" align="center" fixed="right">
          <template #default="{ row }">
            <div class="row-actions">
              <el-button link type="primary" size="small" @click="editItem(row)">{{ $t('common.edit') }}</el-button>
              <el-button link type="danger" size="small" @click="deleteItem(row)">{{ $t('common.delete') }}</el-button>
            </div>
          </template>
        </el-table-column>
      </el-table>

      <el-empty
        v-else
        :description="portfolioStore.error ? '数据加载失败，请点击上方按钮重试' : '暂无持仓数据，点击上方按钮添加'"
      >
        <el-button v-if="!portfolioStore.error" type="primary" @click="showAddDialog = true">添加持仓</el-button>
      </el-empty>
    </section>

    <!-- 添加/编辑对话框 -->
    <el-dialog
      v-model="showAddDialog"
      :title="isEdit ? $t('portfolio.editPosition') : $t('portfolio.addPosition')"
      width="600px"
    >
      <!-- 编辑模式 -->
      <el-form v-if="isEdit" :model="form" label-width="100px">
        <el-form-item :label="$t('home.fundList.code')">
          <el-input v-model="form.fund_code" :disabled="true" />
        </el-form-item>
        <el-form-item :label="$t('home.fundList.name')">
          <el-input v-model="form.fund_name" :disabled="true" />
        </el-form-item>
        <el-form-item :label="$t('portfolio.holdShares')">
          <el-input-number v-model="form.hold_shares" :min="0" :precision="2" class="full-width-control" />
        </el-form-item>
        <el-form-item :label="$t('portfolio.costPrice')">
          <el-input-number v-model="form.cost_nav" :min="0" :precision="4" class="full-width-control" />
        </el-form-item>
      </el-form>

      <!-- 添加模式 -->
      <el-form v-else :model="form" label-width="100px">
        <el-form-item :label="$t('home.fundList.code')">
          <el-select
            v-model="selectedFund"
            filterable
            remote
            reserve-keyword
            placeholder="输入基金代码或名称搜索"
            :remote-method="searchFunds"
            :loading="searchLoading"
            class="full-width-control"
            @change="onFundSelect"
          >
            <el-option
              v-for="item in searchResults"
              :key="item.code"
              :label="`${item.code} - ${item.name}`"
              :value="item"
            />
          </el-select>
        </el-form-item>

        <el-form-item :label="$t('home.fundList.name')">
          <el-input v-model="form.fund_name" :disabled="true" />
        </el-form-item>

        <el-form-item label="昨日净值" v-if="form.previous_nav">
          <div class="previous-nav-display">
            <span class="nav-value">{{ form.previous_nav.toFixed(4) }}</span>
            <el-tag size="small" type="info">已自动填入成本价</el-tag>
          </div>
        </el-form-item>

        <el-form-item :label="$t('portfolio.holdShares')">
          <el-input-number v-model="form.hold_shares" :min="0" :precision="2" class="full-width-control" />
        </el-form-item>
        <el-form-item :label="$t('portfolio.costPrice')">
          <el-input-number v-model="form.cost_nav" :min="0" :precision="4" class="full-width-control" />
        </el-form-item>
      </el-form>

      <template #footer>
        <el-button @click="showAddDialog = false">{{ $t('common.cancel') }}</el-button>
        <el-button type="primary" @click="saveItem">{{ $t('common.confirm') }}</el-button>
      </template>
    </el-dialog>

    <!-- 导入持仓对话框 -->
    <el-dialog
      v-model="showImportDialog"
      title="导入持仓数据"
      width="1080px"
      class="portfolio-import-dialog"
      destroy-on-close
    >
      <div class="import-workflow">
        <div class="import-stepper" aria-label="导入步骤">
          <div
            v-for="step in importSteps"
            :key="step.key"
            class="import-step"
            :class="{ active: importCurrentStep === step.key, done: step.done }"
          >
            <span class="import-step__index">{{ step.index }}</span>
            <span class="import-step__copy">
              <strong>{{ step.title }}</strong>
              <small>{{ step.summary }}</small>
            </span>
          </div>
        </div>

        <el-tabs v-model="importTab" class="import-tabs">
          <el-tab-pane label="AI识别导入" name="ai">
            <div class="ai-import-content">
              <div v-if="!aiConfigReady" class="ai-config-tip">
                <el-alert type="warning" :closable="false" show-icon>
                  <template #title>
                    请先在 <router-link to="/settings">设置页面</router-link> 配置 AI 模型信息
                  </template>
                </el-alert>
              </div>

              <div class="import-source-grid">
                <section class="import-source-card">
                  <div class="import-source-card__header">
                    <span>截图</span>
                    <el-button v-if="aiImagePreview" link type="danger" size="small" @click="clearAiImage">移除</el-button>
                  </div>
                  <el-upload
                    class="ai-image-uploader"
                    drag
                    action="#"
                    :auto-upload="false"
                    :on-change="handleAiImageChange"
                    :limit="1"
                    :show-file-list="false"
                    accept="image/*"
                  >
                    <div v-if="aiImagePreview" class="ai-image-preview">
                      <img :src="aiImagePreview" alt="持仓截图预览" />
                    </div>
                    <template v-else>
                      <el-icon class="el-icon--upload"><Upload /></el-icon>
                      <div class="el-upload__text">
                        拖拽图片到此处或 <em>点击上传</em>
                      </div>
                    </template>
                  </el-upload>
                </section>

                <aside class="import-status-card">
                  <span class="import-status-card__eyebrow">AI 识别</span>
                  <h4>{{ aiImagePreview ? '截图已就绪' : '等待截图' }}</h4>
                  <div class="import-status-list">
                    <div>
                      <span>模型配置</span>
                      <el-tag size="small" :type="aiConfigReady ? 'success' : 'warning'">
                        {{ aiConfigReady ? '已配置' : '未配置' }}
                      </el-tag>
                    </div>
                    <div>
                      <span>识别结果</span>
                      <strong>{{ importPreview.length > 0 ? `${importPreview.length} 条` : '--' }}</strong>
                    </div>
                    <div>
                      <span>可导入</span>
                      <strong>{{ readyImportCount }}</strong>
                    </div>
                  </div>
                  <el-button
                    type="primary"
                    class="ai-recognize-button"
                    :loading="aiRecognizing"
                    :disabled="!aiImageBase64 || !aiConfigReady"
                    @click="handleAiRecognize"
                  >
                    <el-icon><MagicStick /></el-icon>
                    {{ importPreview.length > 0 ? '重新识别' : '开始识别' }}
                  </el-button>
                  <el-alert
                    v-if="aiRecognizeNotice"
                    class="ai-recognize-notice"
                    :type="aiRecognizeNotice.type"
                    show-icon
                    @close="aiRecognizeNotice = null"
                  >
                    <template #title>
                      {{ aiRecognizeNotice.title }}
                    </template>
                    <div v-if="aiRecognizeNotice.messages.length" class="ai-recognize-notice__messages">
                      <div v-for="(message, index) in aiRecognizeNotice.messages" :key="index">{{ message }}</div>
                    </div>
                  </el-alert>
                  <div class="ai-recognize-log">
                    <div class="ai-recognize-log__header">
                      <span>识别日志</span>
                      <el-tag size="small" :type="aiRecognizing ? 'primary' : 'info'">
                        {{ aiRecognizing ? '运行中' : '待命' }}
                      </el-tag>
                    </div>
                    <ol>
                      <li
                        v-for="entry in aiRecognizeLogs"
                        :key="entry.id"
                        :class="`is-${entry.status}`"
                      >
                        <span>{{ entry.time }}</span>
                        <strong>{{ entry.message }}</strong>
                      </li>
                    </ol>
                  </div>
                </aside>
              </div>
            </div>
          </el-tab-pane>

          <el-tab-pane label="文件导入" name="file">
            <div class="import-dialog-content">
              <div class="import-source-grid">
                <section class="import-source-card">
                  <div class="import-source-card__header">
                    <span>JSON 文件</span>
                    <el-tag v-if="importFile" size="small" type="success">已选择</el-tag>
                  </div>
                  <el-upload
                    class="import-uploader"
                    drag
                    action="#"
                    :auto-upload="false"
                    :on-change="handleImportFileChange"
                    :limit="1"
                    :show-file-list="false"
                    accept=".json"
                  >
                    <el-icon class="el-icon--upload"><Upload /></el-icon>
                    <div class="el-upload__text">
                      拖拽文件到此处或 <em>点击上传</em>
                    </div>
                  </el-upload>
                </section>

                <aside class="import-status-card">
                  <span class="import-status-card__eyebrow">文件导入</span>
                  <h4>{{ importFile?.name || '等待文件' }}</h4>
                  <div class="import-status-list">
                    <div>
                      <span>读取结果</span>
                      <strong>{{ importPreview.length > 0 ? `${importPreview.length} 条` : '--' }}</strong>
                    </div>
                    <div>
                      <span>可导入</span>
                      <strong>{{ readyImportCount }}</strong>
                    </div>
                    <div>
                      <span>需核对</span>
                      <strong>{{ reviewImportCount }}</strong>
                    </div>
                  </div>
                </aside>
              </div>
            </div>
          </el-tab-pane>
        </el-tabs>

        <div v-if="importStats.total_value > 0" class="import-stats">
          <div class="import-stat">
            <span>总金额</span>
            <strong>¥{{ importStats.total_value?.toFixed(2) }}</strong>
          </div>
          <div class="import-stat">
            <span>总收益</span>
            <strong :class="importStats.total_holding_return >= 0 ? 'text-success' : 'text-danger'">
              {{ importStats.total_holding_return >= 0 ? '+' : '' }}¥{{ importStats.total_holding_return?.toFixed(2) }}
            </strong>
          </div>
          <div class="import-stat">
            <span>基金数量</span>
            <strong>{{ importStats.holdings_count }} 只</strong>
          </div>
        </div>

        <div v-if="importLoading" class="import-progress-section">
          <div class="progress-header">
            <span>导入进度</span>
            <span class="progress-text">{{ importProgress.current }}/{{ importProgress.total }} ({{ importProgress.percentage }}%)</span>
          </div>
          <el-progress :percentage="importProgress.percentage" :show-text="false" status="success" />
          <div class="progress-status">
            <span v-if="importProgress.percentage < 30">正在查询基金代码...</span>
            <span v-else-if="importProgress.percentage < 100">正在添加持仓...</span>
            <span v-else>导入完成！</span>
          </div>
        </div>

        <div v-if="importPreview.length > 0 && !importLoading" class="import-preview">
          <div class="preview-header">
            <div>
              <strong>核对导入数据</strong>
              <small>{{ importPreview.length }} 条识别结果</small>
            </div>
            <div class="preview-tags">
              <el-tag type="success">可导入 {{ readyImportCount }}</el-tag>
              <el-tag v-if="reviewImportCount > 0" type="warning">需核对 {{ reviewImportCount }}</el-tag>
            </div>
          </div>
          <el-table :data="importPreview" size="small" border height="340">
            <el-table-column type="index" label="序号" width="50" />
            <el-table-column prop="fund_code" label="基金代码" width="170">
              <template #default="{ row }">
                <el-tag v-if="row.fund_code && row.import_status === 'ready'" size="small" type="success">{{ row.fund_code }}</el-tag>
                <el-select
                  v-else-if="row.candidates?.length"
                  v-model="row.fund_code"
                  size="small"
                  filterable
                  placeholder="选择代码"
                  class="candidate-select"
                  @change="onImportCandidateSelect(row)"
                >
                  <el-option
                    v-for="candidate in row.candidates"
                    :key="candidate.code"
                    :label="`${candidate.code} ${candidate.name}`"
                    :value="candidate.code"
                  />
                </el-select>
                <el-tag v-else-if="row._matchStatus === 'ambiguous'" size="small" type="warning">需确认</el-tag>
                <el-tag v-else-if="row._matchStatus === 'invalid'" size="small" type="danger">异常</el-tag>
                <el-tag v-else-if="row._matchStatus === 'searching'" size="small" type="warning">搜索中...</el-tag>
                <el-tag v-else-if="row._matchStatus === 'not_found'" size="small" type="danger">未找到</el-tag>
                <span v-else>--</span>
              </template>
            </el-table-column>
            <el-table-column prop="fund_name" label="基金名称" min-width="180" show-overflow-tooltip />
            <el-table-column label="手动搜索" min-width="260">
              <template #default="{ row }">
                <el-select
                  v-model="row._manualFundCode"
                  size="small"
                  filterable
                  remote
                  reserve-keyword
                  placeholder="输入代码或名称搜索"
                  :remote-method="createImportFundSearch(row)"
                  :loading="row._searchLoading"
                  class="manual-fund-search"
                  @change="confirmImportFund(row)"
                >
                  <el-option
                    v-for="candidate in row._manualCandidates || []"
                    :key="candidate.code"
                    :label="`${candidate.code} ${candidate.name}`"
                    :value="candidate.code"
                  />
                </el-select>
              </template>
            </el-table-column>
            <el-table-column prop="confidence" label="置信度" width="80" align="right">
              <template #default="{ row }">
                {{ row.confidence ?? 0 }}%
              </template>
            </el-table-column>
            <el-table-column prop="market_value" label="市值" width="110" align="right">
              <template #default="{ row }">
                ¥{{ row.market_value?.toFixed(2) || '--' }}
              </template>
            </el-table-column>
            <el-table-column prop="daily_return" label="昨日收益" width="110" align="right">
              <template #default="{ row }">
                <span :class="(row.daily_return || 0) >= 0 ? 'text-success' : 'text-danger'">
                  {{ (row.daily_return || 0) >= 0 ? '+' : '' }}¥{{ row.daily_return?.toFixed(2) || '0.00' }}
                </span>
              </template>
            </el-table-column>
            <el-table-column prop="holding_return" label="持有收益" width="110" align="right">
              <template #default="{ row }">
                <span :class="row.holding_return >= 0 ? 'text-success' : 'text-danger'">
                  {{ row.holding_return >= 0 ? '+' : '' }}¥{{ row.holding_return?.toFixed(2) || '--' }}
                </span>
              </template>
            </el-table-column>
            <el-table-column prop="current_nav" label="当前净值" width="100" align="right">
              <template #default="{ row }">
                {{ row.current_nav ? row.current_nav.toFixed(4) : '--' }}
              </template>
            </el-table-column>
            <el-table-column prop="estimated_shares" label="推算份额" width="110" align="right">
              <template #default="{ row }">
                {{ row.estimated_shares ? formatNumber(row.estimated_shares) : '--' }}
              </template>
            </el-table-column>
            <el-table-column prop="estimated_cost_nav" label="成本净值" width="100" align="right">
              <template #default="{ row }">
                {{ row.estimated_cost_nav ? row.estimated_cost_nav.toFixed(4) : '--' }}
              </template>
            </el-table-column>
            <el-table-column label="导入状态" min-width="150">
              <template #default="{ row }">
                <div class="import-status-cell">
                  <el-tag size="small" :type="row.import_status === 'ready' ? 'success' : row.import_status === 'invalid' ? 'danger' : 'warning'">
                    {{ row.import_status === 'ready' ? '可导入' : '需核对' }}
                  </el-tag>
                  <span v-if="row.import_reason" class="result-error">{{ row.import_reason }}</span>
                </div>
              </template>
            </el-table-column>
          </el-table>
        </div>

        <div v-if="showImportResults" class="import-results">
          <el-alert
            :title="`导入完成：成功 ${importResults.filter(r => r.status === 'success').length} 条，跳过 ${importResults.filter(r => r.status === 'skipped').length} 条，失败 ${importResults.filter(r => r.status === 'failed').length} 条`"
            :type="importResults.some(r => r.status !== 'success') ? 'warning' : 'success'"
            show-icon
            :closable="false"
            class="import-result-alert"
          />
          <div v-if="importResults.some(r => r.status !== 'success')">
            <div class="result-failed-list">
              <div v-for="(r, idx) in importResults.filter(r => r.status !== 'success')" :key="idx" class="result-failed-item">
                <el-tag :type="r.status === 'skipped' ? 'warning' : 'danger'" size="small">
                  {{ r.status === 'skipped' ? '跳过' : '失败' }}
                </el-tag>
                <span class="result-fund-name">{{ r.fund_name }}</span>
                <span v-if="r.fund_code" class="result-fund-code">({{ r.fund_code }})</span>
                <span class="result-error">{{ r.error }}</span>
              </div>
            </div>
          </div>
        </div>
      </div>

      <template #footer>
        <template v-if="showImportResults">
          <el-button @click="retryFailedImports" v-if="importResults.some(r => r.status !== 'success')">
            重试失败项
          </el-button>
          <el-button type="primary" @click="closeImportDialog">完成</el-button>
        </template>
        <template v-else>
          <el-button @click="closeImportDialog" :disabled="importLoading">取消</el-button>
          <el-button
            type="primary"
            :disabled="readyImportCount === 0 || importLoading"
            :loading="importLoading"
            @click="confirmImport"
          >
            {{ importLoading ? '导入中...' : readyImportCount > 0 ? `导入 ${readyImportCount} 条` : '等待可导入数据' }}
          </el-button>
        </template>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
defineOptions({
  name: 'PortfolioView'
})

import { ref, reactive, computed, nextTick, onMounted, watch } from 'vue'
import { Plus, Refresh, Wallet, TrendCharts, TrendCharts as Percentage, Delete, Upload, Loading, MagicStick } from '@element-plus/icons-vue'
import { useI18n } from 'vue-i18n'
import { usePortfolioStore } from '@/stores/portfolioStore'
import { useFundStore } from '@/stores/fundStore'
import { dataManager } from '@/stores/dataManager'
import type { PortfolioItem } from '@/api/portfolio'
import portfolioApi from '@/api/portfolio'
import fundApi, { type FundSearchItem } from '@/api/fund'
import { ElMessage, ElMessageBox } from 'element-plus'
import type { UploadFile } from 'element-plus'
import { DEFAULT_AI_PROMPT, loadAppSettings } from '@/platform/appSettings'

const { t } = useI18n()
const portfolioStore = usePortfolioStore()
const fundStore = useFundStore()

const showAddDialog = ref(false)
const isEdit = ref(false)
const editingId = ref<number | null>(null)

const searchLoading = ref(false)
const searchResults = ref<FundSearchItem[]>([])
const selectedFund = ref<FundSearchItem | null>(null)

const selectedItems = ref<PortfolioItem[]>([])

const showImportDialog = ref(false)
const importTab = ref('ai')
const portfolioTableRef = ref<{ doLayout: () => void } | null>(null)

interface ImportPreviewItem {
  row_index?: number
  fund_code?: string
  fund_name: string
  raw_fund_name?: string
  market_value?: number
  daily_return?: number
  holding_return?: number
  holding_return_rate?: number | null
  estimated_cost?: number
  current_nav?: number | null
  current_change?: number | null
  estimated_shares?: number | null
  estimated_cost_nav?: number | null
  match_status?: string | null
  confidence?: number | null
  match_reason?: string | null
  warnings?: string[]
  candidates?: Array<{
    code: string
    name: string
    score: number
    reason: string
  }>
  import_status?: 'ready' | 'skipped' | 'invalid'
  import_reason?: string
  status?: 'ready' | 'skipped' | 'invalid'
  reason?: string
  _matchStatus?: string
  _manualFundCode?: string
  _manualCandidates?: FundSearchItem[]
  _searchLoading?: boolean
}

interface ApiErrorLike {
  response?: {
    data?: {
      detail?: string
    }
  }
  message?: string
}

interface AiRecognizeNotice {
  type: 'success' | 'warning' | 'error'
  title: string
  messages: string[]
}

interface AiRecognizeLogEntry {
  id: string
  time: string
  message: string
  status: 'pending' | 'running' | 'success' | 'warning' | 'error'
}

const getErrorMessage = (error: unknown, fallback = '未知错误') => {
  if (error instanceof Error) return error.message
  if (typeof error === 'object' && error !== null) {
    const maybeError = error as ApiErrorLike
    return maybeError.response?.data?.detail || maybeError.message || fallback
  }
  return fallback
}

const importPreview = ref<ImportPreviewItem[]>([])
const importFile = ref<File | null>(null)
const importStats = ref({
  total_value: 0,
  total_holding_return: 0,
  holdings_count: 0
})
const readyImportCount = computed(() => importPreview.value.filter(item => item.import_status === 'ready').length)
const reviewImportCount = computed(() => Math.max(importPreview.value.length - readyImportCount.value, 0))
const importCurrentStep = computed<'source' | 'review' | 'confirm'>(() => {
  if (showImportResults.value || importLoading.value) return 'confirm'
  if (importPreview.value.length > 0) return 'review'
  return 'source'
})
const importSteps = computed(() => [
  {
    key: 'source',
    index: 1,
    title: '上传',
    summary: importTab.value === 'ai' ? '选择持仓截图' : '选择 JSON 文件',
    done: Boolean(aiImageBase64.value || importFile.value)
  },
  {
    key: 'review',
    index: 2,
    title: '核对',
    summary: readyImportCount.value > 0
      ? `${readyImportCount.value} 条可导入`
      : '等待识别结果',
    done: readyImportCount.value > 0
  },
  {
    key: 'confirm',
    index: 3,
    title: '导入',
    summary: showImportResults.value ? '查看结果' : '写入本地持仓',
    done: showImportResults.value
  }
] as const)

// AI识别相关
const aiImageBase64 = ref('')
const aiImagePreview = ref('')
const aiRecognizing = ref(false)
const aiRecognizeNotice = ref<AiRecognizeNotice | null>(null)
const aiRecognizeLogs = ref<AiRecognizeLogEntry[]>([])
const aiConfigState = reactive({
  model: '',
  baseUrl: '',
  apiKey: '',
  prompt: DEFAULT_AI_PROMPT
})

const pushAiRecognizeLog = (message: string, status: AiRecognizeLogEntry['status'] = 'running') => {
  aiRecognizeLogs.value.push({
    id: `${Date.now()}-${Math.random().toString(36).slice(2, 8)}`,
    time: new Date().toLocaleTimeString('zh-CN', { hour12: false }),
    message,
    status
  })
}

const loadAiConfig = () => {
  const settings = loadAppSettings()
  return {
    model: settings.aiModel,
    baseUrl: settings.aiBaseUrl,
    apiKey: settings.aiApiKey,
    prompt: settings.aiPrompt?.trim() || DEFAULT_AI_PROMPT
  }
}

const refreshAiConfigState = () => {
  const config = loadAiConfig()
  Object.assign(aiConfigState, config)
  return config
}

const aiConfigReady = computed(() => {
  return !!(aiConfigState.model && aiConfigState.baseUrl && aiConfigState.apiKey)
})

const form = reactive({
  fund_code: '',
  fund_name: '',
  hold_shares: 0,
  cost_amount: 0,
  cost_nav: 0,
  previous_nav: null as number | null
})

const formatNumber = (num: number | string | null | undefined): string => {
  const value = typeof num === 'string' ? parseFloat(num) : Number(num)
  
  if (isNaN(value) || !isFinite(value)) {
    return '0.00'
  }
  
  return value.toLocaleString('zh-CN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })
}

const toNumber = (value: unknown, fallback = 0): number => {
  if (typeof value === 'number') return Number.isFinite(value) ? value : fallback
  if (typeof value === 'string') {
    const parsed = Number(value)
    return Number.isFinite(parsed) ? parsed : fallback
  }
  return fallback
}

const buildImportHoldingsPayload = (items: ImportPreviewItem[]) => items.map((item, index) => ({
  row_index: item.row_index || index + 1,
  fund_code: item.fund_code || undefined,
  fund_name: item.fund_name,
  raw_fund_name: item.raw_fund_name,
  market_value: toNumber(item.market_value),
  daily_return: toNumber(item.daily_return),
  holding_return: toNumber(item.holding_return),
  holding_return_rate: item.holding_return_rate === null || item.holding_return_rate === undefined
    ? null
    : toNumber(item.holding_return_rate),
  match_status: item.match_status || undefined,
  confidence: item.confidence ?? undefined,
  match_reason: item.match_reason || undefined
}))

const mergeImportPreview = (sourceItems: ImportPreviewItem[], previewItems: ImportPreviewItem[]) => {
  return sourceItems.map((source, index) => {
    const preview = previewItems[index]
    return {
      ...source,
      fund_code: preview?.fund_code || source.fund_code,
      fund_name: preview?.fund_name || source.fund_name,
      raw_fund_name: preview?.raw_fund_name || source.raw_fund_name,
      row_index: preview?.row_index || source.row_index || index + 1,
      market_value: toNumber(preview?.market_value ?? source.market_value),
      daily_return: toNumber(preview?.daily_return ?? source.daily_return),
      holding_return: toNumber(preview?.holding_return ?? source.holding_return),
      holding_return_rate: preview?.holding_return_rate === null || preview?.holding_return_rate === undefined
        ? (source.holding_return_rate ?? null)
        : toNumber(preview.holding_return_rate),
      estimated_cost: toNumber(preview?.estimated_cost),
      current_nav: preview?.current_nav === null || preview?.current_nav === undefined ? null : toNumber(preview.current_nav),
      current_change: preview?.current_change === null || preview?.current_change === undefined ? null : toNumber(preview.current_change),
      estimated_shares: preview?.estimated_shares === null || preview?.estimated_shares === undefined ? null : toNumber(preview.estimated_shares),
      estimated_cost_nav: preview?.estimated_cost_nav === null || preview?.estimated_cost_nav === undefined ? null : toNumber(preview.estimated_cost_nav),
      match_status: preview?.match_status || source.match_status,
      confidence: preview?.confidence ?? source.confidence,
      import_status: preview?.status,
      import_reason: preview?.reason,
      warnings: [...(source.warnings || []), ...(preview?.warnings || [])],
      _matchStatus: preview?.match_status || source.match_status || (preview?.fund_code || source.fund_code ? 'matched' : 'not_found')
    }
  })
}

const refreshImportPreview = async () => {
  if (importPreview.value.length === 0) return
  const preview = await portfolioApi.previewImport({
    strict: true,
    holdings: buildImportHoldingsPayload(importPreview.value)
  })
  importPreview.value = mergeImportPreview(importPreview.value, preview.items)
}

const onImportCandidateSelect = async (row: ImportPreviewItem) => {
  const selected = row.candidates?.find(candidate => candidate.code === row.fund_code)
  if (selected) {
    row.fund_name = selected.name
    row.match_status = 'matched'
    row.confidence = 100
    row.match_reason = 'manual_confirmed'
    row._matchStatus = 'matched'
    row.import_reason = ''
  }

  try {
    await refreshImportPreview()
  } catch (error) {
    console.error('刷新导入预检失败:', error)
    ElMessage.error('刷新导入预检失败，请稍后重试')
  }
}

const searchImportFund = async (row: ImportPreviewItem, keyword: string) => {
  const query = keyword.trim()
  if (!query) {
    row._manualCandidates = []
    return
  }
  row._searchLoading = true
  try {
    row._manualCandidates = await fundApi.search(query, 10)
  } catch (error) {
    console.error('复核基金搜索失败:', error)
    row._manualCandidates = []
    ElMessage.error('基金搜索失败，请稍后重试')
  } finally {
    row._searchLoading = false
  }
}

const createImportFundSearch = (row: ImportPreviewItem) => {
  return (keyword: string) => searchImportFund(row, keyword)
}

const confirmImportFund = async (row: ImportPreviewItem) => {
  const selected = row._manualCandidates?.find(candidate => candidate.code === row._manualFundCode)
  if (!selected) return
  row.fund_code = selected.code
  row.fund_name = selected.name
  row.match_status = 'matched'
  row.confidence = 100
  row.match_reason = 'manual_search_confirmed'
  row._matchStatus = 'matched'
  row.import_reason = ''
  row.candidates = [
    { code: selected.code, name: selected.name, score: 100, reason: 'manual_search_confirmed' },
    ...(row.candidates || []).filter(candidate => candidate.code !== selected.code)
  ]

  try {
    await refreshImportPreview()
    ElMessage.success(`已确认 ${selected.code} ${selected.name}`)
  } catch (error) {
    console.error('刷新导入预检失败:', error)
    ElMessage.error('刷新导入预检失败，请稍后重试')
  }
}

const getProfitClass = (row: PortfolioItem) => {
  const profit = (row.profit_amount || 0)
  if (profit > 0) return 'text-success'
  if (profit < 0) return 'text-danger'
  return ''
}

const refreshData = async () => {
  try {
    await portfolioStore.refreshPortfolio()
    if (!portfolioStore.error) {
      ElMessage.success(t('common.success'))
    }
  } catch (e) {
    console.error('刷新持仓数据失败:', e)
  }
}

// 清除缓存数据
const clearCache = () => {
  localStorage.removeItem('fund_tracker_portfolio_items')
  localStorage.removeItem('fund_tracker_portfolio_stats')
  localStorage.removeItem('fund_tracker_portfolio_fetch_time')
  localStorage.removeItem('fund_tracker_fund_list')
  localStorage.removeItem('fund_tracker_realtime_data')
  localStorage.removeItem('fund_tracker_realtime_fetch_time')
  portfolioStore.clearError()
  window.location.reload()
}

const searchFunds = async (query: string) => {
  if (!query || query.length < 2) {
    searchResults.value = []
    return
  }

  searchLoading.value = true
  try {
    const results = await fundApi.search(query, 20)
    searchResults.value = results
  } catch (e) {
    console.error('搜索基金失败:', e)
    searchResults.value = []
  } finally {
    searchLoading.value = false
  }
}

const onFundSelect = async (fund: FundSearchItem) => {
  if (!fund) return

  form.fund_code = fund.code
  form.fund_name = fund.name

  try {
    const fundData = await fundApi.getRealtime(fund.code)
    if (fundData && fundData.previous_nav) {
      form.previous_nav = fundData.previous_nav
      form.cost_nav = fundData.previous_nav
    } else if (fundData && fundData.estimate_nav) {
      form.cost_nav = fundData.estimate_nav
    }
  } catch (e) {
    console.error('获取基金详情失败:', e)
  }
}

const editItem = (row: PortfolioItem) => {
  isEdit.value = true
  editingId.value = row.id || null
  form.fund_code = row.fund_code
  form.fund_name = row.fund_name || ''
  form.hold_shares = row.hold_shares || 0
  form.cost_amount = row.cost_amount || 0
  form.cost_nav = row.cost_nav || 0
  form.previous_nav = null
  selectedFund.value = null
  showAddDialog.value = true
}

const handleSelectionChange = (selection: PortfolioItem[]) => {
  selectedItems.value = selection
}

const batchDelete = async () => {
  if (selectedItems.value.length === 0) return

  try {
    await ElMessageBox.confirm(
      `确定要删除选中的 ${selectedItems.value.length} 条持仓吗？`,
      '确认批量删除',
      {
        confirmButtonText: '确定',
        cancelButtonText: '取消',
        type: 'warning'
      }
    )

    const ids = selectedItems.value
      .map(item => item.id)
      .filter((id): id is number => id !== undefined && id !== null)

    if (ids.length === 0) {
      ElMessage.warning('没有有效的持仓数据可删除')
      return
    }

    const results = await Promise.allSettled(
      ids.map(id => portfolioStore.deleteItem(id))
    )

    const succeeded = results.filter(r => r.status === 'fulfilled' && r.value === true).length
    const failed = results.length - succeeded

    if (failed === 0) {
      ElMessage.success(`成功删除 ${succeeded} 条持仓`)
    } else if (succeeded === 0) {
      ElMessage.error(`删除失败：${failed} 条持仓未能删除`)
    } else {
      ElMessage.warning(`删除完成：成功 ${succeeded} 条，失败 ${failed} 条`)
    }

    selectedItems.value = []
  } catch (error) {
    if (error !== 'cancel' && error !== 'close') {
      console.error('批量删除失败:', error)
      ElMessage.error('批量删除操作失败，请重试')
    }
  }
}

const deleteItem = async (row: PortfolioItem) => {
  if (!row.id) {
    ElMessage.error('无效的持仓数据，无法删除')
    return
  }

  try {
    await ElMessageBox.confirm(
      `确定要删除 ${row.fund_name || '该持仓'} 的持仓吗？`,
      '确认删除',
      {
        confirmButtonText: '确定',
        cancelButtonText: '取消',
        type: 'warning'
      }
    )

    const success = await portfolioStore.deleteItem(row.id)
    if (success) {
      ElMessage.success('删除成功')
    }
  } catch (error) {
    if (error !== 'cancel' && error !== 'close') {
      console.error('删除失败:', error)
      ElMessage.error('删除操作失败，请重试')
    }
  }
}

const saveItem = async () => {
  if (!form.fund_code || !form.fund_name) {
    ElMessage.warning('请填写基金代码和名称')
    return
  }

  if (form.hold_shares <= 0) {
    ElMessage.warning('请输入有效的持有份额')
    return
  }

  if (form.cost_nav <= 0) {
    ElMessage.warning('请输入有效的成本价')
    return
  }

  const costAmount = form.cost_nav * form.hold_shares

  const itemData = {
    fund_code: form.fund_code,
    fund_name: form.fund_name,
    hold_shares: form.hold_shares,
    cost_amount: costAmount,
    cost_nav: form.cost_nav
  }

  const success = isEdit.value && editingId.value
    ? await portfolioStore.updateItem(editingId.value, itemData)
    : await portfolioStore.addItem(itemData)

  if (success) {
    ElMessage.success(isEdit.value ? '更新成功' : '添加成功')
    showAddDialog.value = false
    resetForm()
  }
}

const resetForm = () => {
  form.fund_code = ''
  form.fund_name = ''
  form.hold_shares = 0
  form.cost_amount = 0
  form.cost_nav = 0
  form.previous_nav = null
  isEdit.value = false
  editingId.value = null
  selectedFund.value = null
  searchResults.value = []
}

onMounted(() => {
  console.log('[PortfolioView] 页面已挂载，数据由 DataManager 统一管理')
  refreshAiConfigState()
})

watch(
  () => [portfolioStore.items.length, portfolioStore.loading],
  async () => {
    await nextTick()
    portfolioTableRef.value?.doLayout()
  },
  { flush: 'post' }
)

watch(showImportDialog, (visible) => {
  if (visible) {
    const config = refreshAiConfigState()
    clearAiRecognitionResult()
    if (config.model && config.baseUrl && config.apiKey) {
      pushAiRecognizeLog(`已读取当前模型配置：${config.model}`, 'success')
    }
  }
})

const handleAiImageChange = (uploadFile: UploadFile) => {
  const file = uploadFile.raw
  if (!file) return

  clearAiRecognitionResult()
  const reader = new FileReader()
  reader.onload = (e) => {
    const result = e.target?.result as string
    aiImageBase64.value = result
    aiImagePreview.value = result
  }
  reader.readAsDataURL(file)
}

const clearAiImage = () => {
  aiImageBase64.value = ''
  aiImagePreview.value = ''
  clearAiRecognitionResult()
}

const handleAiRecognize = async () => {
  if (!aiImageBase64.value) {
    aiRecognizeNotice.value = {
      type: 'warning',
      title: '请先上传持仓截图',
      messages: []
    }
    ElMessage.warning('请先上传持仓截图')
    return
  }

  const config = refreshAiConfigState()
  if (!config.model || !config.baseUrl || !config.apiKey) {
    aiRecognizeNotice.value = {
      type: 'warning',
      title: '请先在设置页面配置 AI 模型信息',
      messages: ['配置完成后可以先使用“测试连接”确认接口可用。']
    }
    ElMessage.warning('请先在设置页面配置 AI 模型信息')
    return
  }

  aiRecognizing.value = true
  aiRecognizeNotice.value = null
  aiRecognizeLogs.value = []
  pushAiRecognizeLog('读取模型配置和截图数据')
  try {
    pushAiRecognizeLog(`调用 ${config.model} 进行图片识别，等待模型返回`)
    const result = await portfolioApi.aiRecognize({
      image_base64: aiImageBase64.value,
      model: config.model,
      base_url: config.baseUrl,
      api_key: config.apiKey,
      prompt: config.prompt || undefined
    })

    if (result.holdings && result.holdings.length > 0) {
      pushAiRecognizeLog(`模型返回 ${result.holdings.length} 条持仓，开始匹配基金代码`, 'success')
      const sourceItems: ImportPreviewItem[] = result.holdings.map((h, index) => ({
        ...h,
        row_index: h.row_index || index + 1
      }))
      pushAiRecognizeLog('调用本地基金数据源预检导入可行性')
      const preview = await portfolioApi.previewImport({
        strict: true,
        holdings: buildImportHoldingsPayload(sourceItems)
      })

      importPreview.value = mergeImportPreview(sourceItems, preview.items)
      importStats.value = {
        total_value: result.total_value || 0,
        total_holding_return: result.total_holding_return || 0,
        holdings_count: result.holdings_count || result.holdings.length
      }

      const notFoundCount = result.holdings.filter((h) => h.match_status === 'not_found').length
      const reviewCount = result.holdings.filter((h) => h.match_status === 'ambiguous' || h.match_status === 'invalid').length
      const noticeMessages = buildAiRecognizeNoticeMessages(result, preview.ready_count)
      if (result.warnings?.length) {
        ElMessage.warning(result.warnings.join('；'))
      }
      if (notFoundCount > 0 || reviewCount > 0 || preview.ready_count < result.holdings.length) {
        pushAiRecognizeLog(`完成：${preview.ready_count} 条可导入，${result.holdings.length - preview.ready_count} 条需要人工核对`, 'warning')
        aiRecognizeNotice.value = {
          type: 'warning',
          title: `AI识别完成：${result.holdings.length} 条数据，${preview.ready_count} 条可导入`,
          messages: noticeMessages
        }
        ElMessage.warning(`AI识别出 ${result.holdings.length} 条数据，${preview.ready_count} 条可导入，${result.holdings.length - preview.ready_count} 条需要核对`)
      } else {
        pushAiRecognizeLog('完成：全部持仓通过预检，可直接导入', 'success')
        aiRecognizeNotice.value = {
          type: 'success',
          title: `AI识别完成：${result.holdings.length} 条持仓全部可导入`,
          messages: noticeMessages
        }
        ElMessage.success(`AI识别出 ${result.holdings.length} 条持仓数据，全部可导入`)
      }
    } else {
      throw new Error('AI未识别出任何持仓数据')
    }
  } catch (error: unknown) {
    console.error('AI识别失败:', error)
    const errMsg = getErrorMessage(error)
    aiRecognizeNotice.value = {
      type: 'error',
      title: 'AI识别失败',
      messages: [errMsg, '请先在设置页使用“测试连接”检查模型、Base URL 和 API Key。']
    }
    pushAiRecognizeLog(`失败：${errMsg}`, 'error')
    ElMessage.error('AI识别失败: ' + errMsg)
  } finally {
    aiRecognizing.value = false
  }
}

const handleImportFileChange = (uploadFile: UploadFile) => {
  const file = uploadFile.raw
  if (!file) return

  importFile.value = file

  const reader = new FileReader()
  reader.onload = async (e) => {
    try {
      const content = e.target?.result as string
      const data = JSON.parse(content)

      if (data.holdings && Array.isArray(data.holdings)) {
        const sourceItems: ImportPreviewItem[] = data.holdings.map((h: ImportPreviewItem, index: number) => ({
          ...h,
          row_index: h.row_index || index + 1,
          market_value: toNumber(h.market_value),
          daily_return: toNumber(h.daily_return),
          holding_return: toNumber(h.holding_return)
        }))
        const preview = await portfolioApi.previewImport({
          strict: true,
          holdings: buildImportHoldingsPayload(sourceItems)
        })

        importPreview.value = mergeImportPreview(sourceItems, preview.items)

        importStats.value = {
          total_value: data.total_value || 0,
          total_holding_return: data.total_holding_return || 0,
          holdings_count: data.holdings_count || data.holdings.length
        }

        ElMessage.success(`成功读取 ${data.holdings.length} 条持仓数据，其中 ${preview.ready_count} 条可导入`)
      } else {
        ElMessage.error('文件格式不正确，缺少 holdings 字段')
      }
    } catch (error) {
      console.error('解析文件失败:', error)
      ElMessage.error('文件解析失败，请检查 JSON 格式')
    }
  }
  reader.readAsText(file)
}

const importLoading = ref(false)
const importProgress = ref({
  current: 0,
  total: 0,
  percentage: 0
})

const pendingItems = ref<{ id: number; fund_name: string }[]>([])

interface ImportResultItem {
  fund_name: string
  fund_code: string
  status: 'success' | 'skipped' | 'failed'
  error?: string
}

const importResults = ref<ImportResultItem[]>([])
const showImportResults = ref(false)

const resetImportStats = () => {
  importStats.value = {
    total_value: 0,
    total_holding_return: 0,
    holdings_count: 0
  }
}

const clearAiRecognitionResult = () => {
  aiRecognizeNotice.value = null
  aiRecognizeLogs.value = []
  importPreview.value = []
  importResults.value = []
  showImportResults.value = false
  resetImportStats()
}

const buildAiRecognizeNoticeMessages = (
  result: Awaited<ReturnType<typeof portfolioApi.aiRecognize>>,
  readyCount: number
) => {
  const messages: string[] = []
  if (result.expected_count && result.expected_count !== result.holdings.length) {
    messages.push(`截图显示全部 ${result.expected_count} 条，当前识别到 ${result.holdings.length} 条，请核对是否漏识别。`)
  }
  if (readyCount < result.holdings.length) {
    messages.push(`${result.holdings.length - readyCount} 条暂不能直接导入，请在预览表中确认基金代码或异常原因。`)
  }
  messages.push(...(result.warnings || []))

  const rowWarnings = result.holdings.flatMap(item => {
    const name = item.raw_fund_name || item.fund_name || `第 ${item.row_index || ''} 行`
    return (item.warnings || []).map(warning => `第 ${item.row_index || '-'} 行 ${name}：${warning}`)
  })
  messages.push(...rowWarnings.slice(0, 6))
  if (rowWarnings.length > 6) {
    messages.push(`还有 ${rowWarnings.length - 6} 条行级提示，请查看预览表。`)
  }

  return Array.from(new Set(messages)).slice(0, 10)
}

const confirmImport = async () => {
  if (importPreview.value.length === 0) {
    ElMessage.warning('没有数据可导入')
    return
  }

  if (readyImportCount.value === 0) {
    ElMessage.warning('当前没有通过预检的持仓，请先核对基金代码')
    return
  }

  importLoading.value = true
  showImportResults.value = false
  importResults.value = []
  const totalCount = importPreview.value.length
  importProgress.value = { current: 0, total: totalCount, percentage: 0 }

  try {
    const result = await portfolioApi.confirmImport({
      strict: true,
      holdings: buildImportHoldingsPayload(importPreview.value)
    })

    importResults.value = result.items.map(item => ({
      fund_name: item.fund_name,
      fund_code: item.fund_code,
      status: item.status,
      error: item.error || undefined
    }))
    importProgress.value = { current: totalCount, total: totalCount, percentage: 100 }

    if (result.success_count > 0) {
      ElMessage.success(`成功导入 ${result.success_count} 条持仓`)
    }

    if (result.skipped_count > 0 || result.failed_count > 0) {
      showImportResults.value = true
    } else {
      showImportDialog.value = false
      importPreview.value = []
      importFile.value = null
      resetImportStats()
    }

    await dataManager.refreshPortfolio()
    await nextTick()
    portfolioTableRef.value?.doLayout()
  } catch (e: unknown) {
    const errMsg = getErrorMessage(e)
    ElMessage.error('导入失败: ' + errMsg)
    console.error('[Import] 批量导入失败:', e)
  } finally {
    importLoading.value = false
  }
}

const retryFailedImports = () => {
  const failedKeys = new Set(
    importResults.value
      .filter(r => r.status === 'failed' || r.status === 'skipped')
      .map(r => `${r.fund_code || ''}:${r.fund_name}`)
  )
  const failedItems = importPreview.value.filter(item => failedKeys.has(`${item.fund_code || ''}:${item.fund_name}`))

  importPreview.value = failedItems
  importResults.value = []
  showImportResults.value = false

  if (failedItems.length > 0) {
    ElMessage.info(`已加载 ${failedItems.length} 条失败项，请补充市值信息后重试`)
  }
}

const closeImportDialog = () => {
  showImportDialog.value = false
  showImportResults.value = false
  importPreview.value = []
  importResults.value = []
  importFile.value = null
  aiImageBase64.value = ''
  aiImagePreview.value = ''
  aiRecognizeNotice.value = null
  resetImportStats()
}

const completeMissingData = async (items: { tempId: number; fund_name: string; cost_amount: number }[]) => {
  let completedCount = 0
  let failedCount = 0

  for (const [i, item] of items.entries()) {
    try {
      const cachedFund = fundStore.getFundByName(item.fund_name)
      if (cachedFund) {
        await updatePortfolioFundCode(item.tempId, cachedFund.code, cachedFund.name)
        completedCount++
        continue
      }

      try {
        const searchResults = await fundApi.search(item.fund_name, 5)

        if (searchResults && searchResults.length > 0) {
          const match = searchResults.find(r =>
            r.name.includes(item.fund_name) || item.fund_name.includes(r.name)
          )
          const fundInfo = match ?? searchResults[0]!

          await updatePortfolioFundCode(item.tempId, fundInfo.code, fundInfo.name)
          completedCount++
        } else {
          failedCount++
          pendingItems.value.push({ id: item.tempId, fund_name: item.fund_name })
        }
      } catch (searchError) {
        console.error(`[Complete] 搜索失败: ${item.fund_name}`, searchError)
        failedCount++
        pendingItems.value.push({ id: item.tempId, fund_name: item.fund_name })
      }

      if ((i + 1) % 3 === 0) {
        await new Promise(resolve => setTimeout(resolve, 200))
      }
    } catch (e: unknown) {
      console.error(`[Complete] 补全失败: ${item.fund_name}`, e)
      failedCount++
      pendingItems.value.push({ id: item.tempId, fund_name: item.fund_name })
    }

    importProgress.value = {
      current: i + 1,
      total: items.length,
      percentage: 50 + Math.round(((i + 1) / items.length) * 50)
    }
  }

  importLoading.value = false
  importProgress.value = { current: 0, total: 0, percentage: 0 }

  if (completedCount > 0) {
    ElMessage.success(`已自动补全 ${completedCount} 条持仓数据`)
  }
  if (failedCount > 0) {
    ElMessage.warning(`${failedCount} 条持仓需要手动补全数据，点击"补全数据"按钮处理`)
  }

  await dataManager.refreshPortfolio()
}

const updatePortfolioFundCode = async (id: number, fundCode: string, fundName: string) => {
  try {
    await portfolioApi.update(id, {
      fund_code: fundCode,
      fund_name: fundName
    })
  } catch (e) {
    console.error(`[Update] 更新失败: id=${id}`, e)
  }
}

const completeAllPending = async () => {
  if (pendingItems.value.length === 0) {
    ElMessage.info('没有需要补全的数据')
    return
  }

  importLoading.value = true
  const items = [...pendingItems.value]
  pendingItems.value = []

  await completeMissingData(items.map(item => ({
    tempId: item.id,
    fund_name: item.fund_name,
    cost_amount: 0
  })))
}
</script>

<style scoped lang="scss">
.portfolio-view {
  .portfolio-metrics {
    grid-template-columns: repeat(4, minmax(0, 1fr));
  }

  .portfolio-toolbar {
    padding-block: 16px;
  }

  .portfolio-list {
    min-height: 360px;
  }

  .portfolio-table {
    width: 100%;
    min-height: 260px;
  }

  .portfolio-table :deep(.el-table__body-wrapper) {
    min-height: 0;
  }

  .error-note {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 12px;
    margin-bottom: 16px;
    padding: 14px 16px;
    border: 1px solid rgba(220, 38, 38, 0.16);
    border-radius: var(--radius-base);
    background: var(--danger-light);
    color: var(--danger-color);
    font-size: 13px;
    line-height: 1.5;

    strong {
      margin-right: 6px;
    }
  }

  .table-note {
    margin-bottom: 10px;
    color: var(--text-secondary);
    font-size: 12px;
    font-weight: 600;
  }

  .row-actions {
    display: flex;
    gap: 8px;
    justify-content: center;
  }

  .full-width-control,
  .ai-recognize-button {
    width: 100%;
  }

  .ai-recognize-button {
    margin-top: 12px;
  }

  .ai-recognize-notice {
    margin-top: 12px;
  }

  .ai-recognize-notice__messages {
    display: flex;
    flex-direction: column;
    gap: 4px;
    margin-top: 6px;
    color: var(--text-secondary);
    font-size: 12px;
    line-height: 1.5;
  }

  .ai-recognize-log {
    margin-top: 12px;
    padding: 10px;
    border: 1px solid var(--border-light);
    border-radius: var(--radius-base);
    background: var(--bg-page);

    ol {
      display: flex;
      flex-direction: column;
      gap: 6px;
      max-height: 150px;
      margin: 8px 0 0;
      padding: 0;
      overflow-y: auto;
      list-style: none;
    }

    li {
      display: grid;
      grid-template-columns: 62px minmax(0, 1fr);
      gap: 8px;
      color: var(--text-secondary);
      font-size: 12px;
      line-height: 1.4;

      &.is-success strong {
        color: var(--success-color);
      }

      &.is-warning strong {
        color: var(--warning-color);
      }

      &.is-error strong {
        color: var(--danger-color);
      }
    }

    span {
      color: var(--text-tertiary);
      font-variant-numeric: tabular-nums;
    }

    strong {
      color: var(--text-primary);
      font-weight: 700;
    }
  }

  .ai-recognize-log__header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 8px;
    color: var(--text-primary);
    font-size: 12px;
    font-weight: 850;
  }

  .import-result-alert {
    margin-bottom: 12px;
  }

  .candidate-select {
    width: 140px;
  }

  .manual-fund-search {
    width: 100%;
  }

  .text-success {
    color: var(--success-color);
    font-weight: 700;
  }

  .text-danger {
    color: var(--danger-color);
    font-weight: 700;
  }

  .fund-code-cell {
    display: flex;
    align-items: center;
  }

  .fund-code-loading {
    display: flex;
    align-items: center;
    gap: 6px;
    color: var(--text-secondary);
    font-size: 12px;

    .is-loading {
      animation: rotating 2s linear infinite;
    }

    .loading-text {
      color: var(--text-secondary);
    }
  }

  @keyframes rotating {
    from {
      transform: rotate(0deg);
    }
    to {
      transform: rotate(360deg);
    }
  }

  .previous-nav-display {
    display: flex;
    align-items: center;
    gap: 12px;

    .nav-value {
      font-size: 16px;
      font-weight: 600;
      color: var(--text-primary);
    }
  }

  .import-workflow {
    display: flex;
    flex-direction: column;
    gap: 14px;
  }

  .import-stepper {
    display: grid;
    grid-template-columns: repeat(3, minmax(0, 1fr));
    gap: 10px;
  }

  .import-step {
    display: grid;
    grid-template-columns: 30px minmax(0, 1fr);
    align-items: center;
    gap: 10px;
    padding: 10px 12px;
    border: 1px solid var(--border-light);
    border-radius: var(--radius-base);
    background: var(--bg-page);
    color: var(--text-secondary);
  }

  .import-step.active {
    border-color: rgba(37, 99, 235, 0.24);
    background: rgba(37, 99, 235, 0.06);
    color: var(--text-primary);
  }

  .import-step.done .import-step__index {
    background: var(--success-color);
    color: #fff;
  }

  .import-step__index {
    width: 30px;
    height: 30px;
    display: grid;
    place-items: center;
    border-radius: var(--radius-full);
    background: var(--icon-surface);
    color: var(--primary-color);
    font-size: 13px;
    font-weight: 800;
  }

  .import-step__copy {
    min-width: 0;

    strong,
    small {
      display: block;
      overflow: hidden;
      text-overflow: ellipsis;
      white-space: nowrap;
    }

    strong {
      color: inherit;
      font-size: 13px;
      font-weight: 850;
    }

    small {
      margin-top: 2px;
      color: var(--text-secondary);
      font-size: 12px;
      font-weight: 600;
    }
  }

  .import-tabs {
    :deep(.el-tabs__header) {
      margin-bottom: 12px;
    }
  }

  .ai-config-tip {
    margin-bottom: 12px;

    a {
      color: var(--primary-color);
      text-decoration: underline;
    }
  }

  .import-source-grid {
    display: grid;
    grid-template-columns: minmax(0, 1.45fr) minmax(260px, 0.75fr);
    align-items: stretch;
    gap: 14px;
  }

  .import-source-card,
  .import-status-card {
    min-width: 0;
    padding: 14px;
    border: 1px solid var(--border-light);
    border-radius: var(--radius-base);
    background: var(--bg-card);
  }

  .import-source-card {
    display: flex;
    flex-direction: column;
  }

  .import-source-card__header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 10px;
    margin-bottom: 10px;

    span {
      color: var(--text-primary);
      font-size: 14px;
      font-weight: 850;
    }
  }

  .ai-image-uploader,
  .import-uploader {
    flex: 1;
    display: flex;

    :deep(.el-upload) {
      width: 100%;
      display: flex;
      flex: 1;
    }

    :deep(.el-upload-dragger) {
      width: 100%;
      min-height: 260px;
      height: 100%;
      display: flex;
      align-items: center;
      justify-content: center;
      padding: 16px;
      border-radius: var(--radius-base);
      background: var(--bg-page);
    }
  }

  .ai-image-preview {
    width: 100%;
    height: 100%;
    display: grid;
    place-items: center;

    img {
      max-width: 100%;
      max-height: 228px;
      border: 1px solid var(--border-light);
      border-radius: var(--radius-base);
      object-fit: contain;
      box-shadow: var(--shadow-light);
    }
  }

  .import-status-card {
    display: flex;
    flex-direction: column;

    h4 {
      margin: 4px 0 14px;
      color: var(--text-primary);
      font-size: 18px;
      font-weight: 850;
      line-height: 1.25;
      word-break: break-word;
    }
  }

  .import-status-card .ai-recognize-log {
    margin-top: auto;
  }

  .import-status-card__eyebrow {
    color: var(--text-secondary);
    font-size: 11px;
    font-weight: 850;
  }

  .import-status-list {
    display: flex;
    flex-direction: column;
    gap: 8px;
    margin-bottom: 14px;

    div {
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 12px;
      padding: 9px 10px;
      border: 1px solid var(--border-light);
      border-radius: var(--radius-base);
      background: var(--bg-page);
    }

    span {
      color: var(--text-secondary);
      font-size: 12px;
      font-weight: 700;
    }

    strong {
      color: var(--text-primary);
      font-size: 13px;
      font-weight: 850;
    }
  }

  .import-stats {
    display: grid;
    grid-template-columns: repeat(3, minmax(0, 1fr));
    gap: 10px;
  }

  .import-stat {
    padding: 12px;
    border: 1px solid var(--border-light);
    border-radius: var(--radius-base);
    background: var(--bg-page);

    span,
    strong {
      display: block;
    }

    span {
      color: var(--text-secondary);
      font-size: 12px;
      font-weight: 700;
    }

    strong {
      margin-top: 4px;
      color: var(--text-primary);
      font-size: 16px;
      font-weight: 850;
    }
  }

  .import-preview {
    padding: 14px;
    border: 1px solid var(--border-light);
    border-radius: var(--radius-base);
    background: var(--bg-card);

    .preview-header {
      display: flex;
      justify-content: space-between;
      align-items: center;
      gap: 12px;
      margin-bottom: 12px;
    }

    .preview-header strong,
    .preview-header small {
      display: block;
    }

    .preview-header strong {
      color: var(--text-primary);
      font-size: 14px;
      font-weight: 850;
    }

    .preview-header small {
      margin-top: 2px;
      color: var(--text-secondary);
      font-size: 12px;
      font-weight: 600;
    }
  }

  .preview-tags {
    display: flex;
    flex-wrap: wrap;
    justify-content: flex-end;
    gap: 8px;
  }

  .import-status-cell {
    display: flex;
    flex-direction: column;
    align-items: flex-start;
    gap: 4px;
  }

  .import-results {
    margin: 16px 0;

    .result-failed-list {
      max-height: 200px;
      overflow-y: auto;
      border: 1px solid var(--border-light);
      border-radius: var(--radius-base);
      padding: 8px;

      .result-failed-item {
        display: flex;
        align-items: center;
        gap: 8px;
        padding: 6px 8px;
        font-size: 13px;

        &:not(:last-child) {
          border-bottom: 1px solid var(--border-light);
        }

        .result-fund-name {
          font-weight: 500;
        }

        .result-fund-code {
          color: var(--text-secondary);
          font-size: 12px;
        }

        .result-error {
          color: var(--danger-color);
          font-size: 12px;
          margin-left: auto;
        }
      }
    }
  }

  .import-progress-section {
    margin: 16px 0;
    padding: 20px;
    background: var(--bg-page);
    border-radius: var(--radius-base);

    .progress-header {
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-bottom: 12px;
      font-weight: 500;

      .progress-text {
        color: var(--primary-color);
        font-weight: 600;
      }
    }

    .progress-status {
      margin-top: 12px;
      text-align: center;
      color: var(--text-secondary);
      font-size: 14px;
    }
  }
}
</style>
