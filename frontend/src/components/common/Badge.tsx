import React from 'react';
import { clsx } from 'clsx';
import { twMerge } from 'tailwind-merge';

interface BadgeProps {
  children: React.ReactNode;
  variant?: 'default' | 'critical' | 'high' | 'medium' | 'low' | 'success' | 'brand';
  size?: 'sm' | 'md';
  className?: string;
}

export const Badge: React.FC<BadgeProps> = ({
  children,
  variant = 'default',
  size = 'md',
  className,
}) => {
  const variants = {
    default: 'bg-dark-800 text-slate-300 border border-dark-700',
    critical: 'bg-rose-500/15 text-rose-300 border border-rose-500/30',
    high: 'bg-orange-500/15 text-orange-300 border border-orange-500/30',
    medium: 'bg-amber-500/15 text-amber-300 border border-amber-500/30',
    low: 'bg-blue-500/15 text-blue-300 border border-blue-500/30',
    success: 'bg-emerald-500/15 text-emerald-300 border border-emerald-500/30',
    brand: 'bg-brand-500/15 text-brand-300 border border-brand-500/30',
  };

  const sizes = {
    sm: 'text-xs px-2 py-0.5 font-medium rounded',
    md: 'text-xs px-2.5 py-1 font-medium rounded-md',
  };

  return (
    <span className={twMerge(clsx('inline-flex items-center uppercase tracking-wide', variants[variant], sizes[size], className))}>
      {children}
    </span>
  );
};
