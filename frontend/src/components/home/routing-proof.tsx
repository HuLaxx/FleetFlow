import { InView } from './in-view';

/*
 * Routing benchmark from the P2 Routing Baselines CI job on main (run 45094952454):
 * fixed synthetic scenarios, real OR-Tools CVRPTW against two simple planners.
 */
const methods = [
  { name: 'Input order', note: 'Stops in the order received' },
  { name: 'Nearest neighbour', note: 'Greedy, no backtracking' },
  { name: 'OR-Tools', note: 'Capacity and time windows' },
];

const city = [13.713, 10.23, 10.118];
const windows = [4, 2, 4];

export function RoutingProof() {
  const max = Math.max(...city);
  return (
    <InView className="ffr" threshold={0.35}>
      <div className="ffr__head">
        <span />
        <span>City scenario, 6 stops</span>
        <span>Time-window scenario, 4 stops</span>
      </div>
      {methods.map((m, i) => (
        <div className="ffr__row" key={m.name} data-best={i === 2} style={{ ['--ffr-i' as string]: i }}>
          <div>
            <p className="ffr__name">{m.name}</p>
            <p className="ffr__note">{m.note}</p>
          </div>
          <div className="ffr__cell">
            <span className="ffr__bar" style={{ ['--ffr-w' as string]: city[i] / max }} />
            <span className="ffr__num">{city[i].toFixed(1)} km</span>
          </div>
          <div className="ffr__cell">
            <span className="ffr__stops" aria-label={`${windows[i]} of 4 stops served`}>
              {[0, 1, 2, 3].map((s) => (
                <i key={s} data-served={s < windows[i]} />
              ))}
            </span>
            <span className="ffr__num" data-short={windows[i] < 4}>
              {windows[i]}/4 served
            </span>
          </div>
        </div>
      ))}
      <p className="ffr__foot">
        Nearest neighbour looks almost as short as OR-Tools in the city, until delivery windows bite and it drops half the
        stops. Straight-line distances at a fixed 30 km/h on fixed synthetic fixtures, not road ETAs or fuel savings.
      </p>
    </InView>
  );
}
