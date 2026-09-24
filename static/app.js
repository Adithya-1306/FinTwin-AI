const $ = s => document.querySelector(s);
const $$ = s => [...document.querySelectorAll(s)];
const money = n => '₹' + Number(n || 0).toLocaleString('en-IN', {maximumFractionDigits:0});
let dashboard;

async function api(path, options={}){
  const res = await fetch(path, {headers:{'Content-Type':'application/json'}, ...options});
  const data = await res.json();
  if(!res.ok) throw new Error(data.detail || 'Request failed');
  return data;
}

function activate(id){
  $$('.view').forEach(v=>v.classList.remove('active-view'));
  $(`#${id}`).classList.add('active-view');
  $$('.nav').forEach(n=>n.classList.toggle('active', n.dataset.target===id));
}
$$('.nav').forEach(n=>n.addEventListener('click',()=>activate(n.dataset.target)));

function renderDashboard(d){
  dashboard=d;
  const p=d.profile, h=d.health;
  $('#hello').textContent = `${p.name}, your financial twin is ready.`;
  $('#healthScore').textContent=h.overall;
  document.querySelector('.health-ring').style.background=`conic-gradient(var(--accent) 0 ${h.overall}%, #20314b ${h.overall}%)`;
  $('#heroInsight').textContent=h.messages[0];
  $('#healthBadge').textContent=h.overall>=80?'Strong':h.overall>=65?'Balanced':'Needs attention';
  $('#stats').innerHTML = [
    ['Monthly surplus', money(h.monthly_surplus)],
    ['Savings rate', h.savings_rate+'%'],
    ['Emergency runway', h.emergency_months+' months'],
    ['Risk profile', p.risk_tolerance[0].toUpperCase()+p.risk_tolerance.slice(1)]
  ].map(x=>`<div class="stat"><span>${x[0]}</span><strong>${x[1]}</strong></div>`).join('');
  $('#healthBars').innerHTML=Object.entries(h.components).map(([k,v])=>`<div class="health-row"><span>${k}</span><div class="bar"><i style="width:${v}%"></i></div><strong>${v}</strong></div>`).join('');
  $('#insights').innerHTML=h.messages.map(m=>`<div class="insight">${m}</div>`).join('')+
    `<div class="insight">Your ${p.risk_tolerance} risk setting and ${p.investment_horizon_years}-year horizon are applied to every investment decision.</div>`;
  $('#holdingsTable').innerHTML=d.holdings.map(x=>{
    const val=x.quantity*x.current_price, cost=x.quantity*x.avg_price, pl=val-cost, pct=cost?pl/cost*100:0;
    return `<tr><td><strong>${x.symbol}</strong><br><small>${x.name}</small></td><td>${x.sector}</td><td>${x.quantity}</td><td>${money(x.avg_price)}</td><td>${money(x.current_price)}</td><td>${money(val)}</td><td class="${pl>=0?'positive':'negative'}">${pl>=0?'+':''}${pct.toFixed(1)}%</td></tr>`
  }).join('');
  Object.entries(p).forEach(([k,v])=>{ const el=document.querySelector(`[name="${k}"]`); if(el) el.value=v; });
  renderGoals(d.goals);
}

function renderGoals(goals){
  $('#goalCards').innerHTML=goals.map(g=>{
    const monthly=g.target_amount/(g.years*12);
    return `<div class="goal-card"><span class="priority">${g.priority} priority</span><h3>${g.title}</h3><strong>${money(g.target_amount)}</strong><p>${g.years} years • naive monthly requirement ${money(monthly)}</p><button type="button" class="nav" onclick="deleteGoal(${g.id})">Remove</button></div>`
  }).join('');
}

async function refresh(){ renderDashboard(await api('/api/dashboard')); }

$('#profileForm').addEventListener('submit', async e=>{
  e.preventDefault(); const f=new FormData(e.target);
  const body={name:f.get('name'),age:+f.get('age'),monthly_income:+f.get('monthly_income'),monthly_expenses:+f.get('monthly_expenses'),liquid_savings:+f.get('liquid_savings'),debt_emi:+f.get('debt_emi'),dependents:+f.get('dependents'),risk_tolerance:f.get('risk_tolerance'),investment_horizon_years:+f.get('investment_horizon_years')};
  $('#profileStatus').textContent='Saving…';
  try{await api('/api/profile',{method:'POST',body:JSON.stringify(body)});$('#profileStatus').textContent='Twin updated ✓';await refresh();}catch(err){$('#profileStatus').textContent=err.message;}
});

$('#simCrash').addEventListener('input',e=>$('#crashLabel').textContent=e.target.value+'%');
$('#simJob').addEventListener('input',e=>$('#jobLabel').textContent=e.target.value+' months');
async function runSimulation(){
  const body={monthly_investment:+$('#simMonthly').value,years:+$('#simYears').value,crash_percent:+$('#simCrash').value,job_loss_months:+$('#simJob').value};
  const r=await api('/api/simulate',{method:'POST',body:JSON.stringify(body)});
  $('#baseFinal').textContent=money(r.baseline_final);
  $('#stressFinal').textContent=money(r.stressed_final);
  $('#simSummary').textContent=r.summary;
  drawChart(r.baseline_points,r.stressed_points);
}

$('#simForm').addEventListener('submit',async e=>{
  e.preventDefault();
  try{ await runSimulation(); }
  catch(err){ $('#simSummary').textContent='Simulation unavailable: '+err.message; }
});

function drawChart(a,b){
  const values=[...a,...b].map(x=>x.value); const max=Math.max(...values,1), min=Math.min(...values,0); const span=max-min||1;
  const w=700,h=220,pad=20;
  const pts=(arr)=>arr.map((x,i)=>`${pad+i*(w-2*pad)/(arr.length-1)},${h-pad-(x.value-min)/span*(h-2*pad)}`).join(' ');
  $('#chart').innerHTML=`<svg viewBox="0 0 ${w} ${h}" preserveAspectRatio="none"><line x1="${pad}" y1="${h-pad}" x2="${w-pad}" y2="${h-pad}" stroke="#273a56"/><polyline points="${pts(a)}" fill="none" stroke="#68e0b3" stroke-width="4"/><polyline points="${pts(b)}" fill="none" stroke="#ff7a85" stroke-width="4" stroke-dasharray="8 6"/><text x="24" y="18" fill="#68e0b3" font-size="12">Normal</text><text x="95" y="18" fill="#ff7a85" font-size="12">Stress</text></svg>`;
}

$('#analyzeBtn').addEventListener('click', async () => {
  const card = $('#decisionCard');
  const stockInput = $('#stockInput');
  const symbol = stockInput.value.trim().toUpperCase();

  if (!symbol) {
    card.innerHTML = `
      <p class="negative">
        Please enter a company name or stock symbol.
      </p>
    `;
    return;
  }

  card.innerHTML = `
    <p class="eyebrow">CURRENT DECISION</p>
    <div class="decision-placeholder">
      Fetching live market data and analysing your financial twin…
    </div>
  `;

  try {
    const r = await api('/api/recommendation', {
      method: 'POST',
      body: JSON.stringify({ symbol })
    });

    card.innerHTML = `
      <p class="eyebrow">${r.symbol} • ${r.company}</p>

      <!-- LIVE MARKET DATA -->
      <div class="card-head" style="margin-top:18px;">
        <div>
          <p class="eyebrow">LIVE MARKET DATA</p>

          <div style="display:flex; align-items:baseline; gap:12px;">
            <strong style="font-size:32px;">
              ₹${r.live_price != null
                ? Number(r.live_price).toFixed(2)
                : '--'}
            </strong>

            <span style="
              font-weight:700;
              color:${Number(r.change_percent) >= 0
                ? '#68e0b3'
                : '#ff7a85'};
            ">
              ${r.change_percent != null
                ? (Number(r.change_percent) >= 0 ? '+' : '') +
                  Number(r.change_percent).toFixed(2) + '%'
                : '--'}
            </span>
          </div>

          <small>
            ${r.market_state === 'REGULAR'
              ? '🟢 MARKET OPEN'
              : '⚪ MARKET CLOSED'}
          </small>
        </div>
      </div>

      <!-- MARKET METRICS -->
      <div class="decision-metrics">

        <div>
          <span>Previous Close</span>
          <strong>
            ₹${r.previous_close != null
              ? Number(r.previous_close).toFixed(2)
              : '--'}
          </strong>
        </div>

        <div>
          <span>Day High</span>
          <strong>
            ₹${r.day_high != null
              ? Number(r.day_high).toFixed(2)
              : '--'}
          </strong>
        </div>

        <div>
          <span>Day Low</span>
          <strong>
            ₹${r.day_low != null
              ? Number(r.day_low).toFixed(2)
              : '--'}
          </strong>
        </div>

        <div>
          <span>52W High</span>
          <strong>
            ₹${r.year_high != null
              ? Number(r.year_high).toFixed(2)
              : '--'}
          </strong>
        </div>

      </div>

      <!-- DATA SOURCE -->
      <div style="
        margin:14px 0;
        padding:10px 12px;
        border:1px solid #273a56;
        border-radius:10px;
        font-size:12px;
        display:flex;
        justify-content:space-between;
      ">
        <span>Market data source</span>
        <strong>${r.data_source || 'Live Market Data'}</strong>
      </div>

      <!-- FIN TWIN DECISION -->
      <div class="decision-top">

        <div>
          <p class="eyebrow">FIN TWIN DECISION</p>

          <div class="decision-action ${r.color}">
            ${r.action}
          </div>

          <small>
            ${r.sector} •
            ${r.portfolio_exposure}% portfolio exposure
          </small>
        </div>

        <div class="confidence">
          <span>Confidence</span>
          <strong>${r.confidence}%</strong>
        </div>

      </div>

      <p class="muted-copy">
        ${r.explanation}
      </p>

      <ul class="reason-list">
        ${r.reasons.map(x => `<li>${x}</li>`).join('')}
      </ul>
    `;

  } catch (err) {

    card.innerHTML = `
      <p class="negative">
        ${err.message}
      </p>
    `;
  }
});
$$('.quick-stocks button').forEach(button => {
  button.addEventListener('click', () => {
    $('#stockInput').value = button.dataset.stock;
  });
});

$('#riskForm').addEventListener('submit', async e => {
  e.preventDefault();

  const form = new FormData(e.target);

  const body = {
    market_drop_response: form.get('market_drop_response'),
    income_stability: form.get('income_stability'),
    investment_horizon: form.get('investment_horizon'),
    portfolio_drop_response: form.get('portfolio_drop_response'),
    wealth_priority: form.get('wealth_priority')
  };

  const resultBox = $('#riskResult');

  resultBox.innerHTML = `
    <p class="eyebrow">YOUR RISK PROFILE</p>
    <div class="decision-placeholder">
      Calculating your financial risk profile…
    </div>
  `;

  try {
    const r = await api('/api/risk-assessment', {
      method: 'POST',
      body: JSON.stringify(body)
    });

    resultBox.innerHTML = `
      <p class="eyebrow">YOUR RISK PROFILE</p>

      <div class="decision-action amber">
        ${r.risk_profile}
      </div>

      <div class="decision-metrics">

        <div>
          <span>Overall</span>
          <strong>${r.overall_score}</strong>
        </div>

        <div>
          <span>Risk Capacity</span>
          <strong>${r.risk_capacity}</strong>
        </div>

        <div>
          <span>Risk Tolerance</span>
          <strong>${r.risk_tolerance}</strong>
        </div>

        <div>
          <span>Risk Need</span>
          <strong>${r.risk_need}</strong>
        </div>

      </div>

      <p class="muted-copy">
        Your profile is based on your financial capacity,
        behavioural responses, investment horizon,
        and long-term growth requirements.
      </p>
    `;

  } catch (err) {
    resultBox.innerHTML = `
      <p class="negative">
        Risk assessment failed: ${err.message}
      </p>
    `;
  }
});

$('#goalForm').addEventListener('submit',async e=>{
  e.preventDefault();
  await api('/api/goals',{method:'POST',body:JSON.stringify({title:$('#goalTitle').value,target_amount:+$('#goalAmount').value,years:+$('#goalYears').value,priority:$('#goalPriority').value})});
  e.target.reset(); await refresh();
});
window.deleteGoal=async id=>{await api('/api/goals/'+id,{method:'DELETE'});await refresh();};



async function boot(){
  try{
    await refresh();
    await runSimulation();
  }catch(err){
    console.error('FinTwin startup failed:', err);
    $('#heroInsight').textContent='Unable to load FinTwin data. Check the server window and refresh once.';
    $('#healthBadge').textContent='Connection error';
  }
}

boot();
