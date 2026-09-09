export default function ConfidenceBadge({ confidence }) {
  const label =
    confidence >= 0.85 ? 'Confirmed' : confidence >= 0.55 ? 'Likely' : 'Needs Verification'
  const cls =
    confidence >= 0.85 ? 'badge ok' : confidence >= 0.55 ? 'badge warn' : 'badge low'
  return (
    <span className={cls}>
      <span className={`dot ${cls.split(' ')[1]}`} /> {label} · {Math.round(confidence * 100)}%
    </span>
  )
}