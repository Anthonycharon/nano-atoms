"use client";

interface Props {
  value: string;
  onChange: (value: string) => void;
  captchaSvg: string | null;
  loading: boolean;
  isCyber: boolean;
  onRefresh: () => void;
}

export default function AuthCaptchaField({
  value,
  onChange,
  captchaSvg,
  loading,
  isCyber,
  onRefresh,
}: Props) {
  return (
    <div>
      <label className={`mb-1.5 block text-sm ${isCyber ? "text-slate-300" : "text-slate-600"}`}>
        验证码
      </label>
      <div className="flex items-center gap-3">
        <div
          className={`flex h-14 min-w-[168px] items-center justify-center overflow-hidden rounded-2xl border ${
            isCyber ? "border-cyan-400/15 bg-slate-900/80" : "border-slate-300 bg-white"
          }`}
        >
          {captchaSvg ? (
            // eslint-disable-next-line @next/next/no-img-element
            <img src={captchaSvg} alt="captcha" className="h-full w-full object-cover" />
          ) : (
            <span className={`text-xs ${isCyber ? "text-slate-500" : "text-slate-400"}`}>
              正在加载验证码...
            </span>
          )}
        </div>
        <button
          type="button"
          onClick={onRefresh}
          disabled={loading}
          className={`rounded-2xl border px-4 py-3 text-sm font-medium transition-colors disabled:opacity-50 ${
            isCyber
              ? "border-cyan-400/15 bg-slate-900/80 text-cyan-200 hover:border-cyan-300/40"
              : "border-slate-300 bg-white text-slate-700 hover:border-indigo-400"
          }`}
        >
          换一张
        </button>
      </div>
      <input
        type="text"
        value={value}
        onChange={(event) => onChange(event.target.value.toUpperCase())}
        className={`mt-3 w-full rounded-2xl border px-4 py-3 text-sm uppercase tracking-[0.18em] outline-none transition-colors ${
          isCyber
            ? "border-cyan-400/15 bg-slate-900/80 text-slate-100 placeholder:text-slate-500 focus:border-cyan-300/50"
            : "border-slate-300 bg-white text-slate-900 focus:border-indigo-500"
        }`}
        placeholder="请输入验证码"
        autoComplete="off"
        maxLength={6}
        required
      />
    </div>
  );
}
