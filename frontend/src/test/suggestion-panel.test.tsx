import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it } from 'vitest'

import SuggestionPanel from '../components/SuggestionPanel'
import type { RecommendationResponse } from '../types'

const recommendationFixture: RecommendationResponse = {
    filter_applied: {
        visa_types: ['F1']
    },
    summary: {
        sample_size: 40,
        finalized_cases: 24,
        pending_cases: 16,
        maturity_ratio: 0.6,
        confidence_band: 'medium',
        insufficient_data: false,
        data_freshness_seconds: 300
    },
    items: [
        {
            id: 'approval_probability',
            estimate: 0.7,
            probability_interval_low: 0.62,
            probability_interval_high: 0.78,
            level: 'medium',
            direction: 'higher_is_better',
            reasons: ['clear_ratio', 'sample_size'],
            evidence: [
                { metric: 'clear_ratio', value: 0.7, note: null },
                { metric: 'sample_size', value: 40, note: null }
            ]
        }
    ]
}

describe('SuggestionPanel', () => {
    it('在加载阶段显示 loading 文案', () => {
        render(<SuggestionPanel data={null} loading={true} error={null} />)
        expect(screen.getByText('建议计算中...')).toBeInTheDocument()
    })

    it('在无数据且无错误时显示空态', () => {
        render(<SuggestionPanel data={null} loading={false} error={null} />)
        expect(screen.getByText('当前筛选下暂无可输出建议。')).toBeInTheDocument()
    })

    it('可渲染建议并展开依据', async () => {
        const user = userEvent.setup()
        render(<SuggestionPanel data={recommendationFixture} loading={false} error={null} />)

        expect(screen.getByText('Clear 概率')).toBeInTheDocument()
        expect(screen.getByText('概率: 70% (区间 62% - 78%)')).toBeInTheDocument()

        await user.click(screen.getByRole('button', { name: '展开依据' }))
        expect(screen.getAllByRole('listitem')).toHaveLength(2)

        await user.click(screen.getByRole('button', { name: '收起依据' }))
        expect(screen.queryAllByRole('listitem')).toHaveLength(0)
    })

    it('在错误态显示错误信息', () => {
        render(<SuggestionPanel data={null} loading={false} error={'加载失败'} />)
        expect(screen.getByText('加载失败')).toBeInTheDocument()
    })
})
