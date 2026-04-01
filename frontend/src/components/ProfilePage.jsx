import React, { useState, useEffect, useCallback } from 'react';
import {
  MapPin, Ruler, Wallet, Palette, Baby,
  ArrowLeft, RefreshCw, Pencil, Check, X,
  Users, PawPrint, BookOpen, Plus, TrendingUp,
  CheckCircle2, Circle, ThumbsUp, ThumbsDown, MessageCircle,
  Wrench, DollarSign, BarChart3
} from 'lucide-react';

const STYLE_OPTIONS = ['现代简约', '日式', '北欧', '新中式', '轻奢', '奶油风', '侘寂', '法式', '美式', '工业风'];

function getAuthHeaders() {
  const token = localStorage.getItem('decopilot_token');
  const headers = { 'Content-Type': 'application/json' };
  if (token) headers['Authorization'] = `Bearer ${token}`;
  return headers;
}

export default function ProfilePage({ authUser, theme, onBack }) {
  const [profile, setProfile] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [saving, setSaving] = useState(false);
  const [toast, setToast] = useState(null);

  // Inline editing state — which field is being edited
  const [editing, setEditing] = useState(null);
  const [editValue, setEditValue] = useState('');

  const showToast = useCallback((msg) => {
    setToast(msg);
    setTimeout(() => setToast(null), 2000);
  }, []);

  const fetchProfile = async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await fetch('/api/v1/profile/me', {
        headers: getAuthHeaders(),
        credentials: 'include',
      });
      if (!res.ok) throw new Error('获取档案失败');
      setProfile(await res.json());
    } catch (e) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  };

  const saveField = async (updates) => {
    setSaving(true);
    try {
      const res = await fetch('/api/v1/profile/me', {
        method: 'PUT',
        headers: getAuthHeaders(),
        credentials: 'include',
        body: JSON.stringify(updates),
      });
      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(err.detail || '保存失败');
      }
      const updated = await res.json();
      setProfile(updated);
      showToast('已保存');
    } catch (e) {
      showToast(e.message);
    } finally {
      setSaving(false);
      setEditing(null);
    }
  };

  useEffect(() => { fetchProfile(); }, []);

  const themeColor = theme === 'owner' ? 'owner' : 'merchant';

  if (loading) {
    return (
      <div className="flex-1 flex items-center justify-center">
        <RefreshCw size={20} className="animate-spin text-slate-300" />
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex-1 flex flex-col items-center justify-center gap-3">
        <p className="text-slate-400 text-sm">{error}</p>
        <button onClick={fetchProfile} className="text-sm text-blue-500 hover:underline">重试</button>
      </div>
    );
  }

  if (!profile) return null;

  const budgetMin = profile.budget_range?.min;
  const budgetMax = profile.budget_range?.max;
  const hasAnyInfo = profile.house_area || budgetMin || budgetMax ||
    profile.preferred_styles?.length > 0 || profile.city ||
    profile.family?.has_children || profile.family?.has_elderly || profile.family?.has_pets;

  // --- Edit handlers ---

  const startEdit = (field, currentValue) => {
    setEditing(field);
    setEditValue(currentValue ?? '');
  };

  const cancelEdit = () => {
    setEditing(null);
    setEditValue('');
  };

  const commitEdit = (field) => {
    const val = editValue.toString().trim();
    switch (field) {
      case 'city':
        if (val) saveField({ city: val });
        else cancelEdit();
        break;
      case 'house_area':
        const area = parseFloat(val);
        if (area > 0 && area <= 10000) saveField({ house_area: area });
        else cancelEdit();
        break;
      case 'budget': {
        // Parse "20-30" or "25" format
        const parts = val.replace(/[万元\s]/g, '').split(/[-~～到]/);
        const min = parseFloat(parts[0]) || 0;
        const max = parseFloat(parts[1] || parts[0]) || 0;
        if (max > 0) saveField({ budget_min: min, budget_max: max });
        else cancelEdit();
        break;
      }
      default:
        cancelEdit();
    }
  };

  const toggleStyle = (style) => {
    const current = profile.preferred_styles || [];
    const next = current.includes(style)
      ? current.filter(s => s !== style)
      : [...current, style];
    saveField({ preferred_styles: next });
  };

  const toggleFamily = (field, currentValue) => {
    saveField({ [field]: !currentValue });
  };

  return (
    <div className="flex-1 overflow-y-auto">
      <div className="max-w-[640px] mx-auto px-6 py-6">
        {/* Header */}
        <div className="flex items-center gap-3 mb-6">
          <button
            onClick={onBack}
            className="p-1.5 rounded-lg text-slate-400 hover:text-slate-600 hover:bg-slate-100 transition-colors"
          >
            <ArrowLeft size={18} />
          </button>
          <div className="flex-1">
            <h1 className="text-[17px] font-semibold text-slate-800">我的装修档案</h1>
            <p className="text-[12px] text-slate-400 mt-0.5">智能体了解的关于你的信息 · 点击可修改</p>
          </div>
          <button
            onClick={fetchProfile}
            className="p-1.5 rounded-lg text-slate-300 hover:text-slate-500 hover:bg-slate-100 transition-colors"
          >
            <RefreshCw size={15} />
          </button>
        </div>

        <div className="space-y-4">

          {/* ===== 房屋信息 ===== */}
          <Section title="房屋信息">
            {/* 城市 */}
            <EditableRow
              icon={MapPin}
              label="城市"
              value={profile.city}
              placeholder="点击填写城市"
              editing={editing === 'city'}
              editValue={editValue}
              onStartEdit={() => startEdit('city', profile.city || '')}
              onEditChange={setEditValue}
              onCommit={() => commitEdit('city')}
              onCancel={cancelEdit}
              saving={saving}
            />
            {/* 面积 */}
            <EditableRow
              icon={Ruler}
              label="面积"
              value={profile.house_area ? `${profile.house_area} ㎡` : null}
              placeholder="点击填写面积"
              editing={editing === 'house_area'}
              editValue={editValue}
              inputType="number"
              inputSuffix="㎡"
              onStartEdit={() => startEdit('house_area', profile.house_area || '')}
              onEditChange={setEditValue}
              onCommit={() => commitEdit('house_area')}
              onCancel={cancelEdit}
              saving={saving}
            />
            {/* 预算 */}
            <EditableRow
              icon={Wallet}
              label="预算"
              value={
                budgetMin && budgetMax ? `${budgetMin}-${budgetMax} 万` :
                budgetMax ? `${budgetMax} 万以内` :
                budgetMin ? `${budgetMin} 万起` : null
              }
              placeholder="点击填写预算（如 20-30）"
              editing={editing === 'budget'}
              editValue={editValue}
              inputSuffix="万"
              onStartEdit={() => {
                const v = budgetMin && budgetMax ? `${budgetMin}-${budgetMax}` :
                  budgetMax ? `${budgetMax}` : '';
                startEdit('budget', v);
              }}
              onEditChange={setEditValue}
              onCommit={() => commitEdit('budget')}
              onCancel={cancelEdit}
              saving={saving}
            />
          </Section>

          {/* ===== 风格偏好 ===== */}
          <Section title="风格偏好">
            <div className="flex flex-wrap gap-2">
              {STYLE_OPTIONS.map(style => {
                const selected = (profile.preferred_styles || []).includes(style);
                return (
                  <button
                    key={style}
                    onClick={() => toggleStyle(style)}
                    disabled={saving}
                    className={`text-[12px] px-3 py-1.5 rounded-full border transition-all ${
                      selected
                        ? `bg-${themeColor}-50 text-${themeColor}-600 border-${themeColor}-200 font-medium`
                        : 'bg-white text-slate-500 border-slate-200 hover:border-slate-300'
                    }`}
                  >
                    {selected && <span className="mr-1">✓</span>}
                    {style}
                  </button>
                );
              })}
            </div>
            {(profile.preferred_styles || []).some(s => !STYLE_OPTIONS.includes(s)) && (
              <div className="mt-2 flex flex-wrap gap-1.5">
                {profile.preferred_styles.filter(s => !STYLE_OPTIONS.includes(s)).map(s => (
                  <span key={s} className={`text-[12px] px-3 py-1.5 rounded-full bg-${themeColor}-50 text-${themeColor}-600 border border-${themeColor}-200 font-medium`}>
                    ✓ {s}
                  </span>
                ))}
              </div>
            )}
          </Section>

          {/* ===== 家庭情况 ===== */}
          <Section title="家庭情况">
            <p className="text-[11px] text-slate-400 mb-3">影响环保等级、安全标准和材料推荐</p>
            <div className="space-y-1">
              <ToggleRow
                icon={Baby}
                label="有小孩"
                hint="注意环保和安全防护"
                checked={profile.family?.has_children}
                onChange={() => toggleFamily('has_children', profile.family?.has_children)}
                themeColor={themeColor}
                saving={saving}
              />
              <ToggleRow
                icon={Users}
                label="有老人"
                hint="注意无障碍和防滑设计"
                checked={profile.family?.has_elderly}
                onChange={() => toggleFamily('has_elderly', profile.family?.has_elderly)}
                themeColor={themeColor}
                saving={saving}
              />
              <ToggleRow
                icon={PawPrint}
                label="有宠物"
                hint="注意耐磨和易清洁材料"
                checked={profile.family?.has_pets}
                onChange={() => toggleFamily('has_pets', profile.family?.has_pets)}
                themeColor={themeColor}
                saving={saving}
              />
            </div>
          </Section>

          {/* ===== 我的装修（只读，从对话自动生成） ===== */}
          <RenovationSection renovation={profile.renovation} budgetMax={budgetMax} />

          {/* ===== 近期关注（只读，来自对话） ===== */}
          {profile.interests && Object.keys(profile.interests).length > 0 && (
            <Section title="近期关注" subtitle="从对话中自动识别">
              <div className="flex flex-wrap gap-1.5">
                {Object.entries(profile.interests).map(([topic, weight], i) => (
                  <span
                    key={i}
                    className="text-[12px] px-2.5 py-1 rounded-full bg-slate-50 text-slate-600 border border-slate-100"
                    style={{ opacity: 0.5 + weight * 0.5 }}
                  >
                    {topic}
                  </span>
                ))}
              </div>
            </Section>
          )}

          {/* ===== 对话统计 ===== */}
          {profile.stats && (profile.stats.total_sessions > 0 || profile.stats.total_messages > 0) && (
            <div className="flex gap-3">
              <StatCard value={profile.stats.total_messages} label="对话轮次" />
              <StatCard value={profile.stats.total_sessions} label="会话次数" />
            </div>
          )}

          {/* Footer */}
          <p className="text-center text-[11px] text-slate-300 pt-2 pb-6">
            这些信息帮助智能体给出更个性化的建议
          </p>
        </div>
      </div>

      {/* Toast */}
      {toast && (
        <div className="fixed bottom-8 left-1/2 -translate-x-1/2 z-[70] animate-slide-up">
          <div className="px-4 py-2.5 rounded-xl bg-slate-800 text-white text-[13px] shadow-lg whitespace-nowrap">
            {toast}
          </div>
        </div>
      )}
    </div>
  );
}

/* ========== Sub-components ========== */

function Section({ title, subtitle, children }) {
  return (
    <div className="bg-white rounded-2xl border border-slate-100 p-5">
      <div className="flex items-baseline gap-2 mb-3">
        <h3 className="text-[13px] font-semibold text-slate-700">{title}</h3>
        {subtitle && <span className="text-[11px] text-slate-400">{subtitle}</span>}
      </div>
      {children}
    </div>
  );
}

function EditableRow({
  icon: Icon, label, value, placeholder,
  editing, editValue, inputType, inputSuffix,
  onStartEdit, onEditChange, onCommit, onCancel, saving,
}) {
  if (editing) {
    return (
      <div className="flex items-center gap-3 py-2">
        <Icon size={14} className="text-slate-400 flex-shrink-0" />
        <span className="text-[12px] text-slate-400 w-10 flex-shrink-0">{label}</span>
        <div className="flex-1 flex items-center gap-2">
          <input
            autoFocus
            type={inputType || 'text'}
            value={editValue}
            onChange={e => onEditChange(e.target.value)}
            onKeyDown={e => {
              if (e.key === 'Enter') onCommit();
              if (e.key === 'Escape') onCancel();
            }}
            className="flex-1 text-[13px] text-slate-700 bg-slate-50 border border-slate-200 rounded-lg px-2.5 py-1.5 focus:outline-none focus:border-slate-400"
            placeholder={placeholder}
          />
          {inputSuffix && <span className="text-[12px] text-slate-400">{inputSuffix}</span>}
          <button onClick={onCommit} disabled={saving} className="p-1 rounded text-green-500 hover:bg-green-50">
            <Check size={14} />
          </button>
          <button onClick={onCancel} className="p-1 rounded text-slate-400 hover:bg-slate-100">
            <X size={14} />
          </button>
        </div>
      </div>
    );
  }

  return (
    <button
      onClick={onStartEdit}
      className="w-full flex items-center gap-3 py-2 group text-left hover:bg-slate-50 -mx-2 px-2 rounded-lg transition-colors"
    >
      <Icon size={14} className="text-slate-400 flex-shrink-0" />
      <span className="text-[12px] text-slate-400 w-10 flex-shrink-0">{label}</span>
      {value ? (
        <span className="text-[13px] text-slate-700 flex-1">{value}</span>
      ) : (
        <span className="text-[13px] text-slate-300 flex-1 italic">{placeholder}</span>
      )}
      <Pencil size={12} className="text-slate-300 opacity-0 group-hover:opacity-100 transition-opacity flex-shrink-0" />
    </button>
  );
}

function ToggleRow({ icon: Icon, label, hint, checked, onChange, themeColor, saving }) {
  return (
    <button
      onClick={onChange}
      disabled={saving}
      className="w-full flex items-center gap-3 py-2.5 hover:bg-slate-50 -mx-2 px-2 rounded-lg transition-colors text-left"
    >
      <Icon size={14} className="text-slate-400 flex-shrink-0" />
      <div className="flex-1 min-w-0">
        <span className="text-[13px] text-slate-700">{label}</span>
        {hint && <span className="text-[11px] text-slate-400 ml-2">{hint}</span>}
      </div>
      <div className={`relative w-9 h-5 rounded-full transition-colors ${
        checked ? `bg-${themeColor}-500` : 'bg-slate-200'
      }`}>
        <div className={`absolute top-0.5 w-4 h-4 rounded-full bg-white shadow-sm transition-transform ${
          checked ? 'translate-x-[18px]' : 'translate-x-0.5'
        }`} />
      </div>
    </button>
  );
}

function StatCard({ value, label }) {
  return (
    <div className="flex-1 bg-white rounded-2xl border border-slate-100 p-4 text-center">
      <div className="text-[20px] font-semibold text-slate-700">{value}</div>
      <div className="text-[11px] text-slate-400 mt-0.5">{label}</div>
    </div>
  );
}

/* ========== Renovation Section (我的装修) ========== */

function RenovationSection({ renovation, budgetMax }) {
  // 没有任何装修数据时的空状态
  const hasTodos = renovation?.todos?.length > 0;
  const hasDecisions = renovation?.decisions?.length > 0;
  const hasBrands = renovation?.brand_mentions?.length > 0;
  const hasSpending = renovation?.spending?.length > 0;
  const hasWorkProgress = renovation?.work_progress?.some(w => w.completed);
  const hasAny = hasTodos || hasDecisions || hasBrands || hasSpending || hasWorkProgress;

  if (!hasAny) {
    return (
      <Section title="我的装修" subtitle="从对话自动生成">
        <div className="text-center py-6">
          <p className="text-[13px] text-slate-400">还没有装修记录</p>
          <p className="text-[11px] text-slate-300 mt-1.5 leading-relaxed">
            和我聊聊你的装修——预算多少、选了什么材料、施工到哪一步了
            <br />这里会自动帮你整理成一张清晰的全局图
          </p>
        </div>
      </Section>
    );
  }

  return (
    <div className="space-y-4">
      {/* 施工进度（仅在至少一个工序完成时显示，全灰无信息量） */}
      {renovation?.work_progress?.some(w => w.completed) && (
        <Section title="施工进度" subtitle="从对话自动识别">
          <WorkProgress phases={renovation.work_progress} />
        </Section>
      )}

      {/* 花费追踪 */}
      {hasSpending && (
        <Section title="花费追踪" subtitle="从对话自动提取">
          <BudgetTracker
            spending={renovation.spending}
            budgetSpent={renovation.budget_spent}
            totalSpent={renovation.budget_total_spent}
            budgetMax={budgetMax ? budgetMax * 10000 : null}
          />
        </Section>
      )}

      {/* 待办清单 */}
      {hasTodos && (
        <Section title="待办清单" subtitle="根据你聊过的话题自动生成">
          <TodoList todos={renovation.todos} />
        </Section>
      )}

      {/* 已做决策 */}
      {hasDecisions && (
        <Section title="已做决策" subtitle={`${renovation.decisions.length} 项`}>
          <DecisionsList decisions={renovation.decisions} />
        </Section>
      )}

      {/* 品牌印象 */}
      {hasBrands && (
        <Section title="品牌印象">
          <BrandMentions mentions={renovation.brand_mentions} />
        </Section>
      )}
    </div>
  );
}

function TodoList({ todos }) {
  // 按类别分组
  const grouped = {};
  for (const todo of todos) {
    const cat = todo.category;
    if (!grouped[cat]) grouped[cat] = [];
    grouped[cat].push(todo);
  }

  // 类别排序：基础决策 > 工序 > 选材 > 验收 > 其他
  const categoryOrder = { '基础决策': 0, '工序': 1, '选材': 2, '验收': 3 };
  const sortedCategories = Object.keys(grouped).sort(
    (a, b) => (categoryOrder[a] ?? 9) - (categoryOrder[b] ?? 9)
  );

  return (
    <div className="space-y-4">
      {sortedCategories.map(category => (
        <div key={category}>
          <div className="text-[11px] text-slate-400 font-medium uppercase tracking-wider mb-2">{category}</div>
          <div className="space-y-1.5">
            {grouped[category].map((todo, i) => (
              <div key={i} className="flex items-start gap-2.5 py-1">
                <Circle size={14} className={`mt-0.5 flex-shrink-0 ${
                  todo.priority === 1 ? 'text-red-400' :
                  todo.priority === 2 ? 'text-amber-400' : 'text-slate-300'
                }`} />
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2">
                    <span className="text-[13px] text-slate-700 font-medium">{todo.item}</span>
                    {todo.priority === 1 && (
                      <span className="text-[10px] text-red-500 bg-red-50 px-1.5 py-0.5 rounded">重要</span>
                    )}
                  </div>
                  <p className="text-[11px] text-slate-400 mt-0.5 leading-relaxed">{todo.hint}</p>
                </div>
              </div>
            ))}
          </div>
        </div>
      ))}
    </div>
  );
}

function DecisionsList({ decisions }) {
  // 按品类分组，最近的在前
  const sorted = [...decisions].reverse();
  const grouped = {};
  for (const d of sorted) {
    const cat = d.category || '其他';
    if (!grouped[cat]) grouped[cat] = [];
    grouped[cat].push(d);
  }

  return (
    <div className="space-y-3">
      {Object.entries(grouped).map(([category, items]) => (
        <div key={category}>
          <div className="text-[11px] text-slate-400 font-medium mb-1.5">{category}</div>
          {items.map((d, i) => (
            <div key={i} className="flex items-start gap-2.5 py-1">
              <CheckCircle2 size={14} className="text-green-500 mt-0.5 flex-shrink-0" />
              <div className="flex-1 min-w-0">
                <span className="text-[13px] text-slate-700">{d.text}</span>
                {d.timestamp && (
                  <span className="text-[11px] text-slate-300 ml-2">
                    {new Date(d.timestamp).toLocaleDateString('zh-CN', { month: 'short', day: 'numeric' })}
                  </span>
                )}
              </div>
            </div>
          ))}
        </div>
      ))}
    </div>
  );
}

function BrandMentions({ mentions }) {
  const sentimentConfig = {
    positive: { icon: ThumbsUp, color: 'text-green-600 bg-green-50 border-green-200' },
    negative: { icon: ThumbsDown, color: 'text-red-500 bg-red-50 border-red-200' },
    neutral: { icon: MessageCircle, color: 'text-slate-500 bg-slate-50 border-slate-200' },
  };

  return (
    <div className="flex flex-wrap gap-2">
      {mentions.map((m, i) => {
        const cfg = sentimentConfig[m.sentiment] || sentimentConfig.neutral;
        const SIcon = cfg.icon;
        return (
          <span key={i} className={`inline-flex items-center gap-1 text-[12px] px-2.5 py-1 rounded-full border ${cfg.color}`}>
            <SIcon size={11} />
            {m.brand}
          </span>
        );
      })}
    </div>
  );
}

/* ========== Work Progress (施工进度) ========== */

function WorkProgress({ phases }) {
  if (!phases || phases.length === 0) return null;

  const completedCount = phases.filter(p => p.completed).length;

  return (
    <div>
      {/* 总进度条 */}
      {completedCount > 0 && (
        <div className="mb-3">
          <div className="flex justify-between text-[11px] text-slate-400 mb-1">
            <span>整体进度</span>
            <span>{completedCount}/{phases.length} 完成</span>
          </div>
          <div className="h-1.5 bg-slate-100 rounded-full overflow-hidden">
            <div
              className="h-full bg-gradient-to-r from-green-400 to-green-500 rounded-full transition-all duration-500"
              style={{ width: `${(completedCount / phases.length) * 100}%` }}
            />
          </div>
        </div>
      )}

      {/* 工序标签 */}
      <div className="flex flex-wrap gap-2">
        {phases.map((p, i) => (
          <div
            key={i}
            className={`inline-flex items-center gap-1.5 text-[12px] px-3 py-1.5 rounded-full border transition-colors ${
              p.completed
                ? 'bg-green-50 text-green-700 border-green-200'
                : 'bg-slate-50 text-slate-400 border-slate-200'
            }`}
          >
            {p.completed ? (
              <CheckCircle2 size={13} className="text-green-500" />
            ) : (
              <Circle size={13} className="text-slate-300" />
            )}
            {p.phase}
          </div>
        ))}
      </div>
    </div>
  );
}

/* ========== Budget Tracker (花费追踪) ========== */

function BudgetTracker({ spending, budgetSpent, totalSpent, budgetMax }) {
  if (!spending || spending.length === 0) return null;

  const formatAmount = (amount) => {
    if (amount >= 10000) return `${(amount / 10000).toFixed(1)}万`;
    return `${amount.toFixed(0)}元`;
  };

  // 按品类排序（金额从大到小）
  const sortedCategories = Object.entries(budgetSpent || {}).sort((a, b) => b[1] - a[1]);
  const maxAmount = sortedCategories.length > 0 ? sortedCategories[0][1] : 1;
  const spentTotal = totalSpent || 0;
  const budgetPct = budgetMax && budgetMax > 0 ? Math.min((spentTotal / budgetMax) * 100, 100) : null;
  const isOverBudget = budgetMax && spentTotal > budgetMax;

  return (
    <div>
      {/* 总花费 + 预算对比 */}
      <div className="flex items-center gap-3 mb-4 p-3 bg-slate-50 rounded-xl">
        <div className={`w-10 h-10 rounded-full flex items-center justify-center flex-shrink-0 ${
          isOverBudget ? 'bg-red-50' : 'bg-orange-50'
        }`}>
          <DollarSign size={18} className={isOverBudget ? 'text-red-500' : 'text-orange-500'} />
        </div>
        <div className="flex-1">
          <div className="flex items-baseline gap-1.5">
            <span className={`text-[18px] font-bold ${isOverBudget ? 'text-red-600' : 'text-slate-800'}`}>
              {formatAmount(spentTotal)}
            </span>
            {budgetMax && (
              <span className="text-[12px] text-slate-400">/ {formatAmount(budgetMax)}</span>
            )}
          </div>
          {budgetPct !== null && (
            <div className="mt-1.5">
              <div className="h-1.5 bg-slate-200 rounded-full overflow-hidden">
                <div
                  className={`h-full rounded-full transition-all duration-500 ${
                    isOverBudget ? 'bg-red-500' : budgetPct > 80 ? 'bg-orange-400' : 'bg-green-400'
                  }`}
                  style={{ width: `${budgetPct}%` }}
                />
              </div>
              <div className="text-[10px] text-slate-400 mt-0.5">
                {isOverBudget ? '已超预算' : `已使用 ${budgetPct.toFixed(0)}%`}
              </div>
            </div>
          )}
          {!budgetMax && (
            <div className="text-[11px] text-slate-400">已花费总计</div>
          )}
        </div>
      </div>

      {/* 按品类明细 */}
      {sortedCategories.length > 0 && (
        <div className="space-y-2 mb-4">
          {sortedCategories.map(([cat, amount], i) => (
            <div key={i} className="flex items-center gap-3">
              <span className="text-[12px] text-slate-500 w-16 flex-shrink-0 text-right">{cat}</span>
              <div className="flex-1 h-5 bg-slate-100 rounded-full overflow-hidden">
                <div
                  className="h-full bg-gradient-to-r from-orange-300 to-orange-400 rounded-full transition-all duration-500"
                  style={{ width: `${(amount / maxAmount) * 100}%` }}
                />
              </div>
              <span className="text-[12px] text-slate-700 font-medium w-14 text-right">{formatAmount(amount)}</span>
            </div>
          ))}
        </div>
      )}

      {/* 原始记录 */}
      <details className="group">
        <summary className="text-[11px] text-slate-400 cursor-pointer hover:text-slate-500 transition-colors select-none">
          查看原始记录 ({spending.length} 条)
        </summary>
        <div className="mt-2 space-y-1 pl-1">
          {spending.slice().reverse().map((s, i) => (
            <div key={i} className="flex items-center gap-2 text-[11px]">
              <span className="text-slate-400 w-12 flex-shrink-0">{s.category}</span>
              <span className="text-slate-600 font-medium">
                {s.is_total ? formatAmount(s.amount) : `${s.amount}元/单位`}
              </span>
              {s.timestamp && (
                <span className="text-slate-300 ml-auto">
                  {new Date(s.timestamp).toLocaleDateString('zh-CN', { month: 'short', day: 'numeric' })}
                </span>
              )}
            </div>
          ))}
        </div>
      </details>
    </div>
  );
}
