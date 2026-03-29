import './home-inventory.css'

export type InventoryRow = {
  name: string
  stage: string
  qty: string
  risk: string
  up: boolean
}

export type InventoryProps = {
  rows: InventoryRow[]
  showToast: (message: string) => void
}

export function Inventory({ rows, showToast }: InventoryProps) {
  const totalQty = rows.reduce((acc, r) => acc + Number.parseInt(r.qty, 10), 0)

  return (
    <div className="hi-inventory">
      <header className="hi-inventory__head">
        <div>
          <p className="hi-home__eyebrow">Warehouse</p>
          <h1 className="hi-inventory__title">Inventory</h1>
          <p className="hi-inventory__sub">
            Firefighter drone SKUs · {rows.length} line items · {Number.isFinite(totalQty) ? totalQty : '—'} units
            (rolled)
          </p>
        </div>
        <button
          type="button"
          className="hi-ghost-btn"
          onClick={() => showToast('Export is a demo — wire your ERP when ready')}
        >
          Export snapshot
        </button>
      </header>

      <div className="hi-inventory__table-wrap">
        <div className="hi-inventory__header-row">
          <span>Product</span>
          <span>Stage</span>
          <span>Qty</span>
          <span>Risk</span>
        </div>
        <div className="hi-inventory__body">
          {rows.map((row) => (
            <button
              key={row.name}
              type="button"
              className="hi-inventory__row"
              onClick={() => showToast(`${row.name} · ${row.qty} @ ${row.stage}`)}
            >
              <span className="hi-inventory__cell hi-inventory__cell--product">
                <i className={row.up ? 'hi-dot hi-dot--up' : 'hi-dot hi-dot--down'} aria-hidden="true" />
                {row.name}
              </span>
              <span className="hi-inventory__cell">{row.stage}</span>
              <span className="hi-inventory__cell hi-inventory__cell--qty">{row.qty}</span>
              <span className={`hi-inventory__cell hi-inventory__risk ${row.up ? 'up' : 'down'}`}>{row.risk}</span>
            </button>
          ))}
        </div>
      </div>
    </div>
  )
}
