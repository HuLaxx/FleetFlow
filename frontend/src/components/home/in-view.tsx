'use client';

import { useEffect, useRef, useState, type CSSProperties, type ReactNode } from 'react';

type InViewProps = {
    as?: 'div' | 'ol' | 'section';
    className?: string;
    style?: CSSProperties;
    threshold?: number;
    children: ReactNode;
    'aria-label'?: string;
    role?: string;
};

/** Sets data-visible="true" once the element scrolls into view, so CSS can run a one-off reveal. */
export function InView({ as = 'div', className, style, threshold = 0.3, children, ...rest }: InViewProps) {
    const ref = useRef<HTMLElement | null>(null);
    const [visible, setVisible] = useState(false);

    useEffect(() => {
        const el = ref.current;
        if (!el) return;
        const observer = new IntersectionObserver(
            ([entry]) => {
                if (entry.isIntersecting) {
                    setVisible(true);
                    observer.disconnect();
                }
            },
            { threshold },
        );
        observer.observe(el);
        return () => observer.disconnect();
    }, [threshold]);

    const Tag = as;
    return (
        <Tag
            ref={(node: HTMLElement | null) => {
                ref.current = node;
            }}
            className={className}
            style={style}
            data-visible={visible}
            {...rest}
        >
            {children}
        </Tag>
    );
}
