import React, { useState } from 'react';
import { Home, Store, Eye, EyeOff, Loader2, ArrowRight } from 'lucide-react';

export default function LoginPage({ onLogin }) {
  const [isRegister, setIsRegister] = useState(false);
  const [form, setForm] = useState({
    username: '',
    password: '',
    confirmPassword: '',
    nickname: '',
    phone: '',
    city: '',
    user_type: 'c_end',
  });
  const [showPassword, setShowPassword] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const update = (key, value) => {
    setForm(prev => ({ ...prev, [key]: value }));
    setError('');
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');

    if (!form.username.trim() || !form.password.trim()) {
      setError('请填写用户名和密码');
      return;
    }

    if (isRegister) {
      if (form.password.length < 6) {
        setError('密码至少 6 位');
        return;
      }
      if (form.password !== form.confirmPassword) {
        setError('两次密码不一致');
        return;
      }
    }

    setLoading(true);

    try {
      const endpoint = isRegister ? '/api/v1/auth/register' : '/api/v1/auth/login';
      const body = isRegister
        ? {
            username: form.username.trim(),
            password: form.password,
            user_type: form.user_type,
            nickname: form.nickname.trim() || null,
            phone: form.phone.trim() || null,
            city: form.city.trim() || null,
          }
        : {
            username: form.username.trim(),
            password: form.password,
          };

      const res = await fetch(endpoint, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'include',
        body: JSON.stringify(body),
      });

      const data = await res.json();

      if (!res.ok) {
        setError(data.detail || '操作失败，请重试');
        return;
      }

      // 保存 token 和用户信息
      if (data.token) {
        localStorage.setItem('decopilot_token', data.token);
      }
      localStorage.setItem('decopilot_user', JSON.stringify(data.user));

      onLogin(data.user);
    } catch (err) {
      if (!navigator.onLine) {
        setError('网络已断开，请检查连接');
      } else {
        setError('无法连接到服务器');
      }
    } finally {
      setLoading(false);
    }
  };

  const switchMode = () => {
    setIsRegister(!isRegister);
    setError('');
    setForm(prev => ({ ...prev, password: '', confirmPassword: '' }));
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 via-white to-owner-50 flex items-center justify-center p-4">
      <div className="w-full max-w-md">
        {/* Logo & Title */}
        <div className="text-center mb-8">
          <img
            src="/dongju.png"
            alt="洞居"
            className="w-20 h-20 mx-auto rounded-2xl object-contain mb-4"
          />
          <h1 className="text-2xl font-semibold text-slate-800 tracking-tight">DecoPilot</h1>
          <p className="text-sm text-slate-400 mt-1">洞居智能装修助手</p>
        </div>

        {/* Card */}
        <div className="bg-white rounded-2xl shadow-sm border border-slate-100 p-8">
          <h2 className="text-lg font-medium text-slate-700 mb-6">
            {isRegister ? '创建账号' : '欢迎回来'}
          </h2>

          <form onSubmit={handleSubmit} className="space-y-4">
            {/* 用户名 */}
            <div>
              <label className="block text-[13px] font-medium text-slate-600 mb-1.5">用户名</label>
              <input
                type="text"
                value={form.username}
                onChange={(e) => update('username', e.target.value)}
                placeholder="请输入用户名"
                autoComplete="username"
                className="w-full px-4 py-2.5 rounded-xl border border-slate-200 text-[14px] text-slate-700 placeholder:text-slate-300 focus:outline-none focus:border-owner-400 focus:ring-2 focus:ring-owner-100 transition-all"
              />
            </div>

            {/* 密码 */}
            <div>
              <label className="block text-[13px] font-medium text-slate-600 mb-1.5">密码</label>
              <div className="relative">
                <input
                  type={showPassword ? 'text' : 'password'}
                  value={form.password}
                  onChange={(e) => update('password', e.target.value)}
                  placeholder={isRegister ? '至少 6 位' : '请输入密码'}
                  autoComplete={isRegister ? 'new-password' : 'current-password'}
                  className="w-full px-4 py-2.5 pr-11 rounded-xl border border-slate-200 text-[14px] text-slate-700 placeholder:text-slate-300 focus:outline-none focus:border-owner-400 focus:ring-2 focus:ring-owner-100 transition-all"
                />
                <button
                  type="button"
                  onClick={() => setShowPassword(!showPassword)}
                  className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-500"
                  tabIndex={-1}
                >
                  {showPassword ? <EyeOff size={18} /> : <Eye size={18} />}
                </button>
              </div>
            </div>

            {/* 注册额外字段 */}
            {isRegister && (
              <>
                {/* 确认密码 */}
                <div>
                  <label className="block text-[13px] font-medium text-slate-600 mb-1.5">确认密码</label>
                  <input
                    type="password"
                    value={form.confirmPassword}
                    onChange={(e) => update('confirmPassword', e.target.value)}
                    placeholder="再次输入密码"
                    autoComplete="new-password"
                    className="w-full px-4 py-2.5 rounded-xl border border-slate-200 text-[14px] text-slate-700 placeholder:text-slate-300 focus:outline-none focus:border-owner-400 focus:ring-2 focus:ring-owner-100 transition-all"
                  />
                </div>

                {/* 用户类型 */}
                <div>
                  <label className="block text-[13px] font-medium text-slate-600 mb-1.5">我是</label>
                  <div className="grid grid-cols-2 gap-3">
                    <button
                      type="button"
                      onClick={() => update('user_type', 'c_end')}
                      className={`flex items-center justify-center gap-2 py-2.5 rounded-xl border text-[14px] font-medium transition-all ${
                        form.user_type === 'c_end'
                          ? 'border-owner-400 bg-owner-50 text-owner-600 ring-2 ring-owner-100'
                          : 'border-slate-200 text-slate-500 hover:border-slate-300'
                      }`}
                    >
                      <Home size={16} />
                      <span>业主</span>
                    </button>
                    <button
                      type="button"
                      onClick={() => update('user_type', 'b_end')}
                      className={`flex items-center justify-center gap-2 py-2.5 rounded-xl border text-[14px] font-medium transition-all ${
                        form.user_type === 'b_end'
                          ? 'border-merchant-400 bg-merchant-50 text-merchant-600 ring-2 ring-merchant-100'
                          : 'border-slate-200 text-slate-500 hover:border-slate-300'
                      }`}
                    >
                      <Store size={16} />
                      <span>商家</span>
                    </button>
                  </div>
                </div>

                {/* 昵称 */}
                <div>
                  <label className="block text-[13px] font-medium text-slate-600 mb-1.5">
                    昵称 <span className="text-slate-300 font-normal">（选填）</span>
                  </label>
                  <input
                    type="text"
                    value={form.nickname}
                    onChange={(e) => update('nickname', e.target.value)}
                    placeholder="您的昵称"
                    className="w-full px-4 py-2.5 rounded-xl border border-slate-200 text-[14px] text-slate-700 placeholder:text-slate-300 focus:outline-none focus:border-owner-400 focus:ring-2 focus:ring-owner-100 transition-all"
                  />
                </div>

                {/* 城市 */}
                <div>
                  <label className="block text-[13px] font-medium text-slate-600 mb-1.5">
                    城市 <span className="text-slate-300 font-normal">（选填）</span>
                  </label>
                  <input
                    type="text"
                    value={form.city}
                    onChange={(e) => update('city', e.target.value)}
                    placeholder="您所在的城市"
                    className="w-full px-4 py-2.5 rounded-xl border border-slate-200 text-[14px] text-slate-700 placeholder:text-slate-300 focus:outline-none focus:border-owner-400 focus:ring-2 focus:ring-owner-100 transition-all"
                  />
                </div>
              </>
            )}

            {/* 错误提示 */}
            {error && (
              <div className="text-[13px] text-red-500 bg-red-50 rounded-xl px-4 py-2.5">
                {error}
              </div>
            )}

            {/* 提交按钮 */}
            <button
              type="submit"
              disabled={loading}
              className="w-full flex items-center justify-center gap-2 py-3 rounded-xl bg-gradient-to-r from-owner-500 to-owner-600 text-white text-[15px] font-medium shadow-sm shadow-owner-500/20 hover:shadow-md hover:shadow-owner-500/30 disabled:opacity-60 disabled:cursor-not-allowed transition-all"
            >
              {loading ? (
                <Loader2 size={18} className="animate-spin" />
              ) : (
                <>
                  <span>{isRegister ? '注册' : '登录'}</span>
                  <ArrowRight size={16} />
                </>
              )}
            </button>
          </form>

          {/* 切换登录/注册 */}
          <div className="mt-6 text-center">
            <button
              onClick={switchMode}
              className="text-[13px] text-slate-400 hover:text-owner-500 transition-colors"
            >
              {isRegister ? '已有账号？去登录' : '没有账号？去注册'}
            </button>
          </div>
        </div>

        {/* 底部提示 */}
        <p className="text-center text-[12px] text-slate-300 mt-6">
          DecoPilot · 让装修更简单
        </p>
      </div>
    </div>
  );
}
