import '../pages/home-inventory.css'

export type TeamMember = { name: string; role?: string }

export type TeamCardProps = {
  name: string
  members: TeamMember[]
}

function initials(name: string) {
  return name
    .split(/\s+/)
    .map((p) => p[0])
    .join('')
    .slice(0, 2)
    .toUpperCase()
}

export function TeamCard({ name, members }: TeamCardProps) {
  return (
    <article className="hi-team-card">
      <div className="hi-team-card__head">
        <div className="hi-team-card__badge">Crew</div>
        <h2 className="hi-team-card__title">{name}</h2>
        <p className="hi-team-card__sub">Shift roster · firefighter drone program</p>
      </div>
      <ul className="hi-team-card__list">
        {members.map((m) => (
          <li key={m.name} className="hi-team-card__member">
            <span className="hi-team-card__avatar" aria-hidden="true">
              {initials(m.name)}
            </span>
            <div className="hi-team-card__meta">
              <span className="hi-team-card__name">{m.name}</span>
              {m.role ? <span className="hi-team-card__role">{m.role}</span> : null}
            </div>
          </li>
        ))}
      </ul>
    </article>
  )
}
