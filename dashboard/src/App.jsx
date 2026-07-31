import { useEffect, useMemo, useState } from "react";

const REPO = "https://github.com/Biswajit1999/daily-astro-notebooks";

function Mark() {
  return <span className="mark" aria-hidden="true"><i /><i /><i /></span>;
}

function Arrow() { return <span aria-hidden="true">↗</span>; }

function ResearchModal({item,onClose}) {
  const [figure,setFigure]=useState(0); const figures=item.figures_local?.length?item.figures_local:(item.hero_local?[item.hero_local]:[]);
  return <div className="modal-layer" onMouseDown={onClose}><section className="modal research-modal" role="dialog" aria-modal="true" onMouseDown={e=>e.stopPropagation()}>
    <button className="close" onClick={onClose}>×</button><div className="evidence-panel">{figures[figure]&&<img src={`${import.meta.env.BASE_URL}${figures[figure]}`} alt={`Evidence for ${item.title}`}/>}<div className="figure-tabs">{figures.map((x,i)=><button className={i===figure?'active':''} onClick={()=>setFigure(i)} key={x}>Figure {i+1}</button>)}</div></div>
    <div className="research-copy"><div className="research-badges"><span className={(item.research_level||'').toLowerCase()}>{item.research_level||'Notebook'}</span>{item.claim_type&&<span>{item.claim_type}</span>}</div><p className="meta">{item.archive} · {item.date_display}</p><h2>{item.title}</h2><p className="question">{item.question||item.summary}</p>
    {item.results?.length>0&&<ul>{item.results.map(x=><li key={x}>{x}</li>)}</ul>}{item.quality_checks?.length>0&&<div className="audit-block"><b>Quality checks</b><div className="quality-grid">{item.quality_checks.map(x=><span className={x.status.replace(' ','-')} key={x.name}>{x.name}<small>{x.status}</small></span>)}</div></div>}{item.provenance?.length>0&&<div className="audit-block"><b>Data provenance</b><ol>{item.provenance.map(x=><li key={x}>{x}</li>)}</ol></div>}{item.limitations?.length>0&&<div className="audit-block"><b>Claim boundary</b><p>{item.limitations.join(' · ')}</p></div>}<div className="modal-actions"><a className="primary dark" href={`${REPO}/blob/master/${item.notebook}`}>Open notebook <Arrow/></a>{item.artifacts?.[0]&&<a href={`${REPO}/raw/master/${item.artifacts[0]}`}>Download data ↓</a>}</div></div>
  </section></div>
}

export default function App() {
  const [catalog, setCatalog] = useState({ notebooks: [], stats: {} });
  const [archive, setArchive] = useState("All");
  const [query, setQuery] = useState("");
  const [selected, setSelected] = useState(null);
  const [loadError, setLoadError] = useState(false);

  useEffect(() => {
    fetch(`${import.meta.env.BASE_URL}data/notebooks.json`)
      .then((response) => {
        if (!response.ok) throw new Error("catalog unavailable");
        return response.json();
      })
      .then(setCatalog)
      .catch(() => setLoadError(true));
  }, []);

  const latest = catalog.notebooks.filter((item) => item.dense);
  const audited=catalog.notebooks.filter(item=>['Validated','Exploration'].includes(item.research_level));
  const featured = latest[0];
  const archives = ["All", ...new Set(catalog.notebooks.map((item) => item.family))];
  const shown = useMemo(() => {
    const needle = query.trim().toLowerCase();
    return catalog.notebooks.filter((item) => {
      const matchesArchive = archive === "All" || item.family === archive;
      const haystack = [item.title, item.summary, item.archive, ...(item.tags || []), ...(item.results || [])].join(" ").toLowerCase();
      return matchesArchive && (!needle || haystack.includes(needle));
    });
  }, [catalog, archive, query]);

  return (
    <main>
      <header className="topbar">
        <a className="brand" href="#top"><Mark /><span>Daily Astro <b>Notebooks</b></span></a>
        <nav><a href="#latest">Latest</a><a href="#catalogue">Catalogue</a><a href="#standard">Standard</a></nav>
        <a className="repo-link" href={REPO}>Repository <Arrow /></a>
      </header>

      <section className="hero" id="top">
        <img className="hero-image" src={`${import.meta.env.BASE_URL}data/images/banner.png`} alt="Carina, Eagle and Ring Nebulae blended into a dark astronomical banner" />
        <div className="hero-overlay" /><div className="coordinate-grid" />
        <div className="hero-copy">
          <p className="eyebrow"><span /> Public archive data · analysed daily</p>
          <h1>One sky.<br /><em>A new question every day.</em></h1>
          <p className="lede">Reproducible notebooks that turn real telescope images, spectra, light curves, and catalogues into measured results—with uncertainty and honest limits.</p>
          <div className="hero-actions"><a className="primary" href="#latest">Explore today’s analyses ↓</a><a href="#standard">Read the method <Arrow /></a></div>
        </div>
        {featured && <aside className="result-instrument">
          <div><span>Latest result</span><time>{featured.date_display}</time></div>
          <p>{featured.archive}</p><h2>{featured.title}</h2>
          <strong>{featured.results?.[0]}</strong>
          <small>{featured.sample_size_display}</small>
          <a href={`${REPO}/blob/master/${featured.notebook}`}>Open notebook <Arrow /></a>
        </aside>}
        <div className="stats">
          <div><strong>{catalog.stats.total || "—"}</strong><span>real-data notebooks</span></div>
          <div><strong>{catalog.stats.archives || "—"}</strong><span>public archives</span></div>
          <div><strong>{catalog.stats.dense || "—"}</strong><span>dense analyses</span></div>
          <div><strong>0</strong><span>unlabelled simulations</span></div>
        </div>
      </section>

      <div className="principles"><span>Live archive queries</span><i /><span>Outputs preserved</span><i /><span>Uncertainty reported</span><i /><span>Literature checked</span><i /><span>Limits stated</span></div>
      {audited.length>0&&<section className="audit-strip"><div><p>Scientific audit layer</p><h2>{audited.length} notebooks expose evidence, provenance, and failure limits.</h2></div><div><b>{audited.filter(x=>x.research_level==='Validated').length}</b> validated · <b>{audited.filter(x=>x.research_level==='Exploration').length}</b> exploratory</div></section>}

      <section className="latest" id="latest">
        <div className="section-heading"><div><p>01 / Latest observing log</p><h2>Five questions. Five measured answers.</h2></div><span>Each analysis includes the query, selected data, figures, uncertainty, literature comparison, and a clear boundary around the claim.</span></div>
        {featured && <article className="feature">
          <figure><img src={`${import.meta.env.BASE_URL}${featured.hero_local}`} alt={`Main result plot for ${featured.title}`} /><figcaption>Real archive output · {featured.date_display}</figcaption></figure>
          <div className="feature-copy"><p className="meta">{featured.archive} · {featured.sample_size_display}</p><h3>{featured.title}</h3><p className="question">{featured.question}</p>
            <dl>{featured.results.map((result) => <div key={result}><dt>Measured</dt><dd>{result}</dd></div>)}</dl>
            <div className="validation"><b>Literature check</b><p>{featured.validation}</p></div>
            <a className="primary dark" href={`${REPO}/blob/master/${featured.notebook}`}>Inspect the full analysis <Arrow /></a>
          </div>
        </article>}
      </section>

      <section className="catalogue" id="catalogue">
        <div className="section-heading compact"><div><p>02 / Notebook catalogue</p><h2>Search every result.</h2></div><span>{shown.length} of {catalog.notebooks.length} notebooks shown</span></div>
        <div className="controls"><div className="tabs">{archives.map((item) => <button className={archive === item ? "active" : ""} onClick={() => setArchive(item)} key={item}>{item}</button>)}</div><label><span aria-hidden="true">⌕</span><input aria-label="Search notebooks" placeholder="Search question, target, result…" value={query} onChange={(event) => setQuery(event.target.value)} /></label></div>
        {loadError && <div className="empty"><b>The notebook catalogue could not be loaded.</b><p>The repository remains available from the link above.</p></div>}
        <div className="cards">{shown.map((item, index) => <article className={item.dense ? "card dense" : "card"} key={item.id}>
          <button onClick={() => setSelected(item)} aria-label={`Preview ${item.title}`}>
            {item.hero_local ? <div className="thumb"><img src={`${import.meta.env.BASE_URL}${item.hero_local}`} alt="" /><span>{String(index + 1).padStart(2, "0")}</span></div> : <div className="thumb placeholder"><Mark /><span>{String(index + 1).padStart(2, "0")}</span></div>}
            <div className="card-body">{item.research_level&&<div className="research-badges"><span className={item.research_level.toLowerCase()}>{item.research_level}</span>{item.claim_type&&<span>{item.claim_type}</span>}</div>}<p className="meta">{item.archive} · {item.date_display}</p><h3>{item.title}</h3><p>{item.summary}</p>{item.results?.length > 0 && <strong>{item.results[0]}</strong>}<div>{item.tags?.slice(0, 3).map((tag) => <i key={tag}>{tag}</i>)}</div></div>
          </button><a href={`${REPO}/blob/master/${item.notebook}`}>Open notebook <Arrow /></a>
        </article>)}</div>
        {!loadError && shown.length === 0 && <div className="empty"><b>No matching notebook.</b><p>Try a broader search or another archive.</p></div>}
      </section>

      <section className="standard" id="standard"><div><p className="light">03 / Analysis standard</p><h2>A notebook is finished when the claim is testable.</h2><span>The dense format is designed for learning in public without confusing a plotted pattern with a scientific conclusion.</span></div><ol>{[["Question","One narrow, measurable problem."],["Provenance","Exact archive query or product ID."],["Quality","Missing data, flags, and cuts inspected."],["Uncertainty","Errors, intervals, or resampling."],["Validation","Compared with a paper or physical expectation."],["Limits","What the data cannot establish."]].map(([title,text], index) => <li key={title}><b>0{index+1}</b><div><strong>{title}</strong><span>{text}</span></div></li>)}</ol></section>
      <footer><div className="brand"><Mark /><span>Daily Astro <b>Notebooks</b></span></div><p>Real public astronomy data, analysed by Biswajit.</p><a href={REPO}>GitHub repository <Arrow /></a></footer>

      {selected&&<ResearchModal item={selected} onClose={()=>setSelected(null)}/>}
    </main>
  );
}
