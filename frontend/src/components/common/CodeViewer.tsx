import React, { useEffect, useRef } from 'react';
import { EditorState } from '@codemirror/state';
import { EditorView, lineNumbers, highlightActiveLineGutter, highlightSpecialChars } from '@codemirror/view';
import { javascript } from '@codemirror/lang-javascript';
import { python } from '@codemirror/lang-python';
import { oneDark } from '@codemirror/theme-one-dark';

interface CodeViewerProps {
  code: string;
  language?: string;
  startLine?: number;
  highlightLine?: number;
  className?: string;
}

export const CodeViewer: React.FC<CodeViewerProps> = ({
  code,
  language = 'python',
  startLine = 1,
  className = '',
}) => {
  const containerRef = useRef<HTMLDivElement>(null);
  const viewRef = useRef<EditorView | null>(null);

  useEffect(() => {
    if (!containerRef.current) return;

    // Pick language extension
    const langExt = language.toLowerCase() === 'python' ? python() : javascript();

    const startState = EditorState.create({
      doc: code,
      extensions: [
        lineNumbers({
          formatNumber: (n) => String(n + startLine - 1),
        }),
        highlightActiveLineGutter(),
        highlightSpecialChars(),
        langExt,
        oneDark,
        EditorView.editable.of(false),
        EditorView.theme({
          '&': { height: '100%', fontSize: '13px' },
          '.cm-scroller': { overflow: 'auto', fontFamily: 'JetBrains Mono, monospace' },
          '.cm-gutters': { backgroundColor: '#0b0f19', borderRight: '1px solid #161f33', color: '#475569' },
        }),
      ],
    });

    const view = new EditorView({
      state: startState,
      parent: containerRef.current,
    });

    viewRef.current = view;

    return () => {
      view.destroy();
    };
  }, [code, language, startLine]);

  return (
    <div
      ref={containerRef}
      className={`rounded-lg overflow-hidden border border-dark-700 bg-dark-900 ${className}`}
    />
  );
};
