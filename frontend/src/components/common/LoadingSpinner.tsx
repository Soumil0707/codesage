import React from 'react';

export const LoadingSpinner: React.FC<{ size?: 'sm' | 'md' | 'lg'; text?: string }> = ({
  size = 'md',
  text,
}) => {
  const sizes = {
    sm: 'w-4 h-4',
    md: 'w-8 h-8',
    lg: 'w-12 h-12',
  };

  return (
    <div className="flex flex-col items-center justify-center p-8 gap-3">
      <div className={`${sizes[size]} border-2 border-brand-500/20 border-t-brand-500 rounded-full animate-spin`} />
      {text && <span className="text-sm text-slate-400 animate-pulse">{text}</span>}
    </div>
  );
};
