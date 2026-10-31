import type { ReactNode } from 'react'

interface ShowcaseCardProps {
  title: string
  children: ReactNode
}

export function ShowcaseCard({ title, children }: ShowcaseCardProps) {
  return (
    <article className="showcase-card">
      <h3 className="showcase-card-title">{title}</h3>
      <div className="showcase-card-body">{children}</div>
    </article>
  )
}
