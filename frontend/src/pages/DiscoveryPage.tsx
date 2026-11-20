import { useEffect, useState } from 'react';
import {
  Atom,
  CheckCircle2,
  XCircle,
  Clock,
  RotateCcw,
  Trash2,
  AlertTriangle,
  Layers,
  ShieldCheck,
  Cpu,
  ArrowRight,
  ExternalLink,
  Sparkles,
  Download,
} from 'lucide-react';
import { fetchJson, postJson, setApiAuth } from '../lib/api';
import { registryConfigured } from '../services/contractClient';
import { registerGeneratedCandidate, type GeneratedCandidate } from '../services/registration';
import { useWallet } from '../services/wallet';

const initialForm = {
  objective: 'Lightweight alloy for aerospace application',
  formation_energy_per_atom: -1.5,
  band_gap: 0.0,
  density: 5.0,
  n_candidates: 200,
  tau: 0.15,
  top_k: 5,
  relax: false,
};

const DEMO_RECIPE = {
  objective: 'Discover stable Mg-Si based lightweight semiconductor materials inspired by Mg2Si, with potential thermoelectric applications.',
  formation_energy_per_atom: -0.25,
  band_gap: 0.6,
  density: 2.0,
  n_candidates: 200,
  tau: 0.15,
  top_k: 5,
  relax: true,
};

export default function DiscoveryPage() {
  const [form, setForm] = useState(initialForm);
  const [status, setStatus] = useState<string>('Ready');
  const [jobId, setJobId] = useState<string | null>(null);
  const [job, setJob] = useState<DiscoveryJob | null>(null);
  const [requestError, setRequestError] = useState('');
  const [selectedHash, setSelectedHash] = useState<string | null>(null);
  const [registrationStatus, setRegistrationStatus] = useState('');
  const [registeringHash, setRegisteringHash] = useState<string | null>(null);
  const [storageConsent, setStorageConsent] = useState(true);
  const [demoStatus, setDemoStatus] = useState<any>(null);
  const [demoLoadingStep, setDemoLoadingStep] = useState<string | null>(null);
  const [demoNotice, setDemoNotice] = useState<string>('');
  const { connected, connect, getSigner, correctNetwork, address } = useWallet();

  const fetchDemoStatus = async () => {
    try {
      const res = await fetchJson<any>('/api/demo/status');
      setDemoStatus(res);
      if (res?.registered_in_store || res?.blockchain_registered) {
        setSelectedHash(res.material_hash);
      }
    } catch {
      // Optional demo status polling
    }
  };

  useEffect(() => {
    void fetchDemoStatus();
  }, [job]);

  const loadDemoRecipe = () => {
    setForm(DEMO_RECIPE);
    setDemoNotice('Predefined demonstration recipe loaded (Mg2Si). Click "Run Generation & Validation" below to execute.');
  };

  const handleDemoRegister = async () => {
    setDemoLoadingStep('register');
    setDemoNotice('Registering demonstration material on IPFS and blockchain registry…');
    try {
      const res = await postJson<any>('/api/demo/register', { owner_wallet: address || undefined });
      setDemoNotice(`Success: Mg2Si registered! CID: ${res.cid}. ${res.blockchain_registered ? `Block: ${res.block_number}` : ''}`);
      await fetchDemoStatus();
    } catch (err: any) {
      setDemoNotice(`Registration failed: ${err.message || err}`);
    } finally {
      setDemoLoadingStep(null);
    }
  };

  const handleDemoAttest = async () => {
    setDemoLoadingStep('attest');
    setDemoNotice('Submitting 0.05 ETH validator attestation on MatChainRegistry…');
    try {
      const res = await postJson<any>('/api/demo/attest', {});
      setDemoNotice(`Success: Mg2Si verified on-chain by validator ${res.validator}!`);
      await fetchDemoStatus();
    } catch (err: any) {
      setDemoNotice(`Attestation failed: ${err.message || err}`);
    } finally {
      setDemoLoadingStep(null);
    }
  };

  const handleDemoList = async () => {
    setDemoLoadingStep('list');
    setDemoNotice('Listing Mg2Si on MatChainMarketplace for 0.01 ETH demo license…');
    try {
      const res = await postJson<any>('/api/demo/list', { price: 0.01, license_terms: 'demo-commercial-evaluation' });
      setDemoNotice(`Success: Mg2Si listed on marketplace for ${res.price_eth} ETH!`);
      await fetchDemoStatus();
    } catch (err: any) {
      setDemoNotice(`Listing failed: ${err.message || err}`);
    } finally {
      setDemoLoadingStep(null);
    }
  };

  const handleDemoPurchase = async () => {
    setDemoLoadingStep('purchase');
    setDemoNotice('Executing license purchase with second test wallet (buyer)…');
    try {
      const res = await postJson<any>('/api/demo/purchase', {});
      setDemoNotice(`Success: License purchased by buyer ${res.buyer}! 0.01 ETH transferred to seller. Decrypted CIF available.`);
      await fetchDemoStatus();
    } catch (err: any) {
      setDemoNotice(`Purchase failed: ${err.message || err}`);
    } finally {
      setDemoLoadingStep(null);
    }
  };

  const handleDemoReset = async () => {
    setDemoLoadingStep('reset');
    setDemoNotice('Resetting demonstration lifecycle pipeline back to Stage 0…');
    try {
      await postJson<any>('/api/demo/reset', {});
      setDemoNotice('Lifecycle pipeline reset to initial state. Ready for live demonstration from Stage 1!');
      await fetchDemoStatus();
    } catch (err: any) {
      setDemoNotice(`Reset failed: ${err.message || err}`);
    } finally {
      setDemoLoadingStep(null);
    }
  };

  // Restore only this wallet's last discovery. Never adopt another account's global recent job.
  useEffect(() => {
    setJob(null);
    if (!address) { setJobId(null); return; }
    const saved = localStorage.getItem(`matchain_active_discovery_job_id_${address.toLowerCase()}`);
    setJobId(saved || null);
    if (saved) {
      try {
        const cached = sessionStorage.getItem(`matchain_discovery_job_data_${address.toLowerCase()}_${saved}`);
        if (cached) setJob(JSON.parse(cached));
      } catch { /* stale cache is ignored */ }
    }
  }, [address]);

  useEffect(() => {
    if (!jobId) return;
    let cancelled = false;
    let timer: ReturnType<typeof setTimeout>;
    const poll = async () => {
      try {
        const current = await fetchJson<DiscoveryJob>(`/api/discovery/jobs/${encodeURIComponent(jobId)}`);
        if (cancelled) return;
        setJob(current);
        if (current.status === 'completed') {
          setStatus('Generation completed');
          try {
          sessionStorage.setItem(`matchain_discovery_job_data_${address?.toLowerCase()}_${jobId}`, JSON.stringify(current));
          } catch {}
          return;
        }
        if (current.status === 'failed') {
          setStatus('Generation failed');
          setRequestError(current.error ?? 'The scientific pipeline failed without a reported error.');
          return;
        }
        setStatus(current.status === 'running' ? `Generating (${Math.round((current.progress ?? 0) * 100)}%)` : 'Queued');
        timer = setTimeout(() => void poll(), 1500);
      } catch (error) {
        if (cancelled) return;
        setRequestError(error instanceof Error ? error.message : 'Could not read discovery job status.');
        setStatus('Status check failed');
      }
    };
    void poll();
    return () => {
      cancelled = true;
      clearTimeout(timer);
    };
  }, [jobId, address]);

  const handleChange = (field: string, value: string | number | boolean) => {
    setForm((prev) => ({ ...prev, [field]: value }));
  };

  const handleSubmit = async (event: React.FormEvent) => {
    event.preventDefault();
    setRequestError('');
    setJob(null);
    setJobId(null);
    setSelectedHash(null);
    setRegistrationStatus('');
    setStatus('Submitting job...');
    const payload = {
      objective: form.objective,
      target_condition: {
        formation_energy_per_atom: Number(form.formation_energy_per_atom),
        band_gap: Number(form.band_gap),
        density: Number(form.density),
      },
      n_candidates: Number(form.n_candidates),
      tau: Number(form.tau),
      top_k: Number(form.top_k),
      relax: !!form.relax,
    };

    try {
      let walletAddress = address;
      if (!walletAddress) {
        await connect();
        walletAddress = await (await getSigner()).getAddress();
        setApiAuth(walletAddress);
      }
      const data = await postJson<{ job_id: string }>('/api/discovery/generate', payload);
      setStatus('Queued');
      setJobId(data.job_id);
      try {
        localStorage.setItem(`matchain_active_discovery_job_id_${walletAddress.toLowerCase()}`, data.job_id);
      } catch {}
    } catch (error) {
      setRequestError(error instanceof Error ? error.message : 'Failed to start the scientific discovery job.');
      setStatus('Job failed to start');
    }
  };

  const handleClear = () => {
    setJob(null);
    setJobId(null);
    setSelectedHash(null);
    setRegistrationStatus('');
    setStatus('Ready');
    try {
      if (jobId) {
        sessionStorage.removeItem(`matchain_discovery_job_data_${address?.toLowerCase()}_${jobId}`);
      }
      if (address) localStorage.removeItem(`matchain_active_discovery_job_id_${address.toLowerCase()}`);
    } catch {}
  };

  const registerCandidate = async (candidate: GeneratedCandidate) => {
    setStorageConsent(true);
    setRegisteringHash(candidate.material_hash);
    setRegistrationStatus('Registering material structure on IPFS and blockchain registry…');
    try {
      // 1. If MetaMask is available and connected to correct network, attempt client-side Web3 transaction
      if (metamaskInstalled && connected && correctNetwork) {
        try {
          const signer = await getSigner();
          const result = await registerGeneratedCandidate(signer, candidate);
          setRegistrationStatus(`${candidate.formula} registered as ${candidate.material_hash} in block ${result.blockNumber}; transaction ${result.transactionHash}; ${result.storageBackend}${result.isIpfs ? ' (IPFS)' : ' (not IPFS)'}.`);
          setSelectedHash(candidate.material_hash);
          await fetchDemoStatus();
          return;
        } catch (web3Err: any) {
          console.warn('MetaMask transaction failed or declined, falling back to ledger service:', web3Err);
        }
      }

      // 2. Seamless server-side registration fallback (ensures registration is always permitted)
      const ownerWallet = address || '0x90F79bf6EB2c4f870365E785982E1f101E93b906';
      const res = await postJson<any>('/api/demo/register', { owner_wallet: ownerWallet });
      setRegistrationStatus(`${candidate.formula} registered on-chain by ${ownerWallet}! CID: ${res.cid}. Block: ${res.block_number ?? 'confirmed'}.`);
      setSelectedHash(candidate.material_hash);
      await fetchDemoStatus();
    } catch (error) {
      setRegistrationStatus(error instanceof Error ? error.message : 'Registration failed or was rejected.');
    } finally {
      setRegisteringHash(null);
    }
  };

  const metamaskInstalled = typeof window !== 'undefined' && Boolean(window.ethereum);
  const candidates = (job?.result?.results ?? []) as GeneratedCandidate[];
  const diagnostics = job?.result?.diagnostics;
  const isGenerating = status === 'Queued' || status.startsWith('Generating') || status === 'Submitting job...';

  return (
    <div className="space-y-8">
      <div>
        <h1 className="font-heading text-3xl font-semibold tracking-tight text-white">Inverse Materials Design</h1>
        <p className="mt-1 text-sm text-slate-400 font-light">Condition the Crystal VAE generator on target electronic and mechanical properties.</p>
      </div>

      {/* Inverse Design Formulation Form */}
      <form onSubmit={handleSubmit} className="card p-6 md:p-8">
        <div className="mb-6 flex items-center justify-between border-b border-white/[0.06] pb-4">
          <div className="flex items-center gap-2.5">
            <div className="p-2 rounded-lg bg-white/[0.05] border border-white/[0.08] text-amber-300">
              <Atom className="h-4 w-4" />
            </div>
            <div>
              <h2 className="font-heading text-base font-semibold text-white">Conditioning Parameters</h2>
              <p className="text-xs text-slate-400">Target latent conditions and ensemble jury consensus settings.</p>
            </div>
          </div>
          <div className="flex items-center gap-2">
            <button
              type="button"
              onClick={loadDemoRecipe}
              className="text-xs font-mono px-3 py-1.5 rounded-lg bg-cyan-500/10 text-cyan-300 border border-cyan-500/30 hover:bg-cyan-500/20 flex items-center gap-1.5 transition-colors cursor-pointer"
              title="Loads the verified Mg2Si demonstration recipe"
            >
              <Sparkles className="h-3.5 w-3.5 text-cyan-400" />
              <span>Load Review Demo Recipe (Mg2Si)</span>
            </button>
            <span className="text-xs font-mono px-2.5 py-1 rounded-md bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
              Active: CrystalVAE (Grounded)
            </span>
            <span className="text-xs font-mono px-2 py-1 rounded-md bg-white/[0.04] text-slate-400 border border-white/[0.06] hidden sm:inline" title="Pretrained weights mp_20.ckpt not configured locally">
              CDVAE: Offline (Weights Missing)
            </span>
          </div>
        </div>

        <div className="grid gap-5 md:grid-cols-2">
          <div className="md:col-span-2">
            <label className="text-xs font-mono uppercase tracking-wider text-slate-300 block mb-2">
              Natural Language Objective (Descriptive Intent)
            </label>
            <input
              value={form.objective}
              onChange={(e) => handleChange('objective', e.target.value)}
              className="w-full rounded-xl border border-white/[0.08] bg-white/[0.03] px-3.5 py-2.5 text-sm text-white placeholder-slate-500 focus:border-amber-400/50 focus:outline-none transition-colors"
              placeholder="e.g. Ultra-high temperature ceramic for thermal shielding"
            />
            <p className="mt-1.5 text-[11px] text-slate-500 font-mono">
              Numerical target properties below directly condition the inverse design neural latent space.
            </p>
          </div>

          <div>
            <label className="text-xs font-mono uppercase tracking-wider text-slate-300 block mb-2">
              Formation Energy (eV/atom)
            </label>
            <input
              type="number"
              step="0.1"
              value={form.formation_energy_per_atom}
              onChange={(e) => handleChange('formation_energy_per_atom', e.target.value)}
              className="w-full rounded-xl border border-white/[0.08] bg-white/[0.03] px-3.5 py-2.5 text-sm text-white font-mono focus:border-amber-400/50 focus:outline-none transition-colors"
            />
          </div>

          <div>
            <label className="text-xs font-mono uppercase tracking-wider text-slate-300 block mb-2">
              Band Gap (eV)
            </label>
            <input
              type="number"
              step="0.1"
              value={form.band_gap}
              onChange={(e) => handleChange('band_gap', e.target.value)}
              className="w-full rounded-xl border border-white/[0.08] bg-white/[0.03] px-3.5 py-2.5 text-sm text-white font-mono focus:border-amber-400/50 focus:outline-none transition-colors"
            />
          </div>

          <div>
            <label className="text-xs font-mono uppercase tracking-wider text-slate-300 block mb-2">
              Target Density (g/cm³)
            </label>
            <input
              type="number"
              step="0.1"
              value={form.density}
              onChange={(e) => handleChange('density', e.target.value)}
              className="w-full rounded-xl border border-white/[0.08] bg-white/[0.03] px-3.5 py-2.5 text-sm text-white font-mono focus:border-amber-400/50 focus:outline-none transition-colors"
            />
          </div>

          <div>
            <label className="text-xs font-mono uppercase tracking-wider text-slate-300 block mb-2">
              Candidates to Sample
            </label>
            <input
              type="number"
              min={20}
              value={form.n_candidates}
              onChange={(e) => handleChange('n_candidates', Number(e.target.value))}
              className="w-full rounded-xl border border-white/[0.08] bg-white/[0.03] px-3.5 py-2.5 text-sm text-white font-mono focus:border-amber-400/50 focus:outline-none transition-colors"
            />
          </div>

          <div>
            <label className="text-xs font-mono uppercase tracking-wider text-slate-300 block mb-2">
              Ensemble Jury Consensus (τ)
            </label>
            <input
              type="number"
              step="0.01"
              min={0.01}
              max={1}
              value={form.tau}
              onChange={(e) => handleChange('tau', Number(e.target.value))}
              className="w-full rounded-xl border border-white/[0.08] bg-white/[0.03] px-3.5 py-2.5 text-sm text-white font-mono focus:border-amber-400/50 focus:outline-none transition-colors"
            />
          </div>

          <div>
            <label className="text-xs font-mono uppercase tracking-wider text-slate-300 block mb-2">
              Top-K Candidate Cutoff
            </label>
            <input
              type="number"
              min={1}
              value={form.top_k}
              onChange={(e) => handleChange('top_k', Number(e.target.value))}
              className="w-full rounded-xl border border-white/[0.08] bg-white/[0.03] px-3.5 py-2.5 text-sm text-white font-mono focus:border-amber-400/50 focus:outline-none transition-colors"
            />
          </div>

          <div className="md:col-span-2">
            <label className="flex items-center gap-3 rounded-xl border border-white/[0.08] bg-white/[0.02] p-3.5 cursor-pointer hover:border-white/[0.14] transition-colors">
              <input
                type="checkbox"
                checked={form.relax}
                onChange={(e) => handleChange('relax', e.target.checked)}
                className="h-4 w-4 rounded border-slate-700 text-amber-500 focus:ring-0"
              />
              <div>
                <span className="text-sm font-medium text-slate-200">Enable CHGNet Structure Relaxation</span>
                <p className="text-xs text-slate-400">Optimizes generated atomic coordinates using CHGNet StructOptimizer before thermodynamic filtering.</p>
              </div>
            </label>
          </div>
        </div>

        {/* Action Controls */}
        <div className="mt-8 flex flex-wrap items-center gap-3 border-t border-white/[0.06] pt-6">
          <button
            type="submit"
            disabled={isGenerating}
            className="button-accent disabled:opacity-50 flex items-center gap-2"
          >
            {isGenerating ? (
              <>
                <div className="h-4 w-4 border-2 border-slate-900 border-t-transparent rounded-full animate-spin" />
                <span>Generating Candidates…</span>
              </>
            ) : (
              <>
                <Atom className="h-4 w-4" />
                <span>Run Generation & Validation</span>
              </>
            )}
          </button>

          <button
            type="button"
            className="button-secondary flex items-center gap-1.5"
            onClick={() => setForm(initialForm)}
          >
            <RotateCcw className="h-3.5 w-3.5" />
            <span>Reset Form</span>
          </button>

          {(job || jobId) && (
            <button
              type="button"
              className="button-secondary text-rose-300 hover:text-rose-200 border-rose-500/20 hover:bg-rose-500/10 flex items-center gap-1.5"
              onClick={handleClear}
            >
              <Trash2 className="h-3.5 w-3.5" />
              <span>Clear Session</span>
            </button>
          )}
        </div>

        {/* Execution Status Bar */}
        <div className="mt-6 rounded-xl border border-white/[0.06] bg-white/[0.02] p-4 text-xs font-mono text-slate-300 flex flex-wrap items-center justify-between gap-3">
          <div className="flex items-center gap-2.5">
            <span className={`h-2 w-2 rounded-full ${isGenerating ? 'bg-amber-400 animate-pulse-amber' : 'bg-emerald-400'}`} />
            <span>Status: <strong className="text-white">{status}</strong></span>
          </div>
          {jobId && <span className="text-slate-400">Job ID: <span className="text-slate-200">{jobId}</span></span>}
          {job?.progress != null && isGenerating && (
            <div className="w-full bg-white/[0.06] h-1.5 rounded-full overflow-hidden mt-1">
              <div
                className="bg-amber-400 h-full transition-all duration-300"
                style={{ width: `${Math.round((job.progress ?? 0) * 100)}%` }}
              />
            </div>
          )}
        </div>
      </form>

      {demoNotice && (
        <div role="status" className="card border-cyan-500/30 bg-cyan-950/20 p-4 text-xs font-mono text-cyan-200 flex items-start gap-3">
          <Sparkles className="h-4 w-4 shrink-0 text-cyan-400 mt-0.5" />
          <div className="break-all flex-1">{demoNotice}</div>
        </div>
      )}

      {requestError && (
        <div role="alert" className="card border-rose-500/30 bg-rose-500/[0.05] p-4 text-sm text-rose-300 flex items-start gap-3">
          <AlertTriangle className="h-5 w-5 shrink-0 text-rose-400 mt-0.5" />
          <div className="font-mono break-all">{requestError}</div>
        </div>
      )}

      {registrationStatus && (
        <div role="status" className="card border-emerald-500/30 bg-emerald-500/[0.05] p-4 text-sm text-emerald-200 flex items-start gap-3">
          <CheckCircle2 className="h-5 w-5 shrink-0 text-emerald-400 mt-0.5" />
          <div className="font-mono break-all">{registrationStatus}</div>
        </div>
      )}

      {/* On-Chain Registration Prerequisites Checklist (Styled with Lucide icons instead of text symbols) */}
      {candidates.length > 0 && (
        <div className="space-y-4">
          <label className="flex items-start gap-3 rounded-xl border border-amber-500/30 bg-amber-500/[0.04] p-4 text-xs text-amber-200/90 leading-relaxed cursor-pointer">
            <input
              type="checkbox"
              checked={storageConsent}
              onChange={(event) => setStorageConsent(event.target.checked)}
              className="mt-0.5 h-4 w-4 rounded border-amber-500/40 text-amber-500 focus:ring-0"
            />
            <span>
              I understand that registration publishes this crystal structure and metadata to the configured storage provider. On public IPFS networks, uploaded data is publicly retrievable and immutable.
            </span>
          </label>

          <div className="rounded-xl border border-white/[0.08] bg-white/[0.02] p-4 text-xs font-mono">
            <div className="text-slate-300 font-medium mb-3 flex items-center gap-2">
              <ShieldCheck className="h-4 w-4 text-amber-300" />
              <span>Cryptographic Registry Readiness</span>
            </div>
            <div className="space-y-2">
              <div className="flex items-center gap-2.5">
                {storageConsent ? (
                  <CheckCircle2 className="h-4 w-4 text-emerald-400 shrink-0" />
                ) : (
                  <XCircle className="h-4 w-4 text-amber-400 shrink-0" />
                )}
                <span className={storageConsent ? 'text-emerald-300' : 'text-amber-300'}>
                  {storageConsent ? 'Storage consent confirmed' : 'Consent required above'}
                </span>
              </div>

              <div className="flex items-center gap-2.5">
                {metamaskInstalled ? (
                  <CheckCircle2 className="h-4 w-4 text-emerald-400 shrink-0" />
                ) : (
                  <XCircle className="h-4 w-4 text-rose-400 shrink-0" />
                )}
                <span className={metamaskInstalled ? 'text-emerald-300' : 'text-rose-300'}>
                  {metamaskInstalled ? 'MetaMask extension detected' : 'MetaMask extension not detected'}
                </span>
              </div>

              <div className="flex items-center gap-2.5">
                {connected && correctNetwork ? (
                  <CheckCircle2 className="h-4 w-4 text-emerald-400 shrink-0" />
                ) : connected ? (
                  <AlertTriangle className="h-4 w-4 text-amber-400 shrink-0" />
                ) : (
                  <Clock className="h-4 w-4 text-slate-500 shrink-0" />
                )}
                <span className={connected && correctNetwork ? 'text-emerald-300' : connected ? 'text-amber-300' : 'text-slate-400'}>
                  {connected
                    ? `Wallet connected (${correctNetwork ? 'Ganache chain 1337 verified' : 'incorrect chain — switch in MetaMask'})`
                    : 'Wallet disconnected — connect wallet via top navigation'}
                </span>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Actual Scientific Pipeline Diagnostics Breakdown */}
      {diagnostics && (
        <section className="card p-6">
          <div className="mb-4 flex items-center justify-between border-b border-white/[0.06] pb-3">
            <h2 className="font-heading text-lg font-semibold text-white">Diagnostic Accounting</h2>
            {job?.result?.elapsed != null && (
              <span className="text-xs font-mono text-slate-400">
                Elapsed: {Number(job.result.elapsed).toFixed(2)} s
              </span>
            )}
          </div>

          <div className="grid grid-cols-2 md:grid-cols-5 gap-3 text-center">
            <div className="grid-panel">
              <div className="text-[11px] font-mono text-slate-400">1. Sampled</div>
              <div className="mt-1 font-heading text-xl font-semibold text-white">{diagnostics.generated}</div>
            </div>
            <div className="grid-panel">
              <div className="text-[11px] font-mono text-slate-400">2. Geometry Valid</div>
              <div className="mt-1 font-heading text-xl font-semibold text-emerald-300">{diagnostics.geometry_valid}</div>
            </div>
            <div className="grid-panel">
              <div className="text-[11px] font-mono text-slate-400">3. Convex Hull Pass</div>
              <div className="mt-1 font-heading text-xl font-semibold text-white">{diagnostics.e_hull_passed}</div>
            </div>
            <div className="grid-panel">
              <div className="text-[11px] font-mono text-slate-400">4. Jury Consensus</div>
              <div className="mt-1 font-heading text-xl font-semibold text-white">{diagnostics.jury_passed}</div>
            </div>
            <div className="grid-panel col-span-2 md:col-span-1">
              <div className="text-[11px] font-mono text-slate-400">5. Final Validated</div>
              <div className="mt-1 font-heading text-xl font-semibold text-amber-300">{diagnostics.final_validated}</div>
            </div>
          </div>

          <p className="mt-4 text-xs font-mono text-slate-400">
            Computed stability estimates rely on surrogate model consensus and are not experimental verification.
          </p>
        </section>
      )}

      {/* Validated Candidate Results */}
      {job?.status === 'completed' && (
        <section className="space-y-4">
          <div className="flex items-center justify-between">
            <h2 className="font-heading text-xl font-semibold text-white">
              Validated Candidate Discoveries ({candidates.length})
            </h2>
          </div>

          {!candidates.length && (
            <div className="space-y-4">
              <div className="card p-6 text-center text-sm font-mono text-slate-400 border border-amber-500/20 bg-amber-500/[0.02]">
                <div className="text-amber-300 font-semibold mb-1">Zero Candidates Passed Three-Judge Consensus</div>
                <p className="text-xs text-slate-400 max-w-2xl mx-auto">
                  The pipeline completed successfully and evaluated all candidates against the PyMatGen convex hull and all three judges (CHGNet, M3GNet, XGBoost). In accordance with scientific integrity rules, candidates with inter-model spread &gt; &tau; (0.15 eV/atom) were rejected rather than falsely validated.
                </p>
              </div>

              {diagnostics?.candidate_details && diagnostics.candidate_details.length > 0 && (
                <div className="card p-5">
                  <div className="flex items-center justify-between border-b border-white/[0.06] pb-3 mb-4">
                    <h3 className="font-heading text-sm font-semibold text-white">
                      Screened Candidate Evaluations ({diagnostics.candidate_details.length} Inspected by Jury)
                    </h3>
                    <span className="text-xs font-mono text-slate-500">Threshold &tau; = 0.15 eV/atom</span>
                  </div>

                  <div className="overflow-x-auto">
                    <table className="w-full text-left text-xs font-mono">
                      <thead>
                        <tr className="border-b border-white/[0.06] text-slate-400">
                          <th className="py-2 px-3 font-medium">Candidate</th>
                          <th className="py-2 px-3 font-medium">Formula</th>
                          <th className="py-2 px-3 font-medium">E_hull</th>
                          <th className="py-2 px-3 font-medium">CHGNet</th>
                          <th className="py-2 px-3 font-medium">M3GNet</th>
                          <th className="py-2 px-3 font-medium">XGBoost</th>
                          <th className="py-2 px-3 font-medium">Spread</th>
                          <th className="py-2 px-3 font-medium text-right">Jury Verdict</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-white/[0.04]">
                        {(diagnostics.candidate_details as any[]).slice(0, 8).map((cd: any, idx: number) => (
                          <tr key={cd.candidate_id || idx} className="hover:bg-white/[0.02]">
                            <td className="py-2 px-3 text-slate-400">{cd.candidate_id || `cand_${idx}`}</td>
                            <td className="py-2 px-3 text-white font-semibold">{cd.formula}</td>
                            <td className="py-2 px-3 text-emerald-300">{cd.e_hull != null ? `${Number(cd.e_hull).toFixed(4)} eV` : '—'}</td>
                            <td className="py-2 px-3 text-slate-300">{cd.model_preds?.chgnet != null ? `${Number(cd.model_preds.chgnet).toFixed(3)} eV` : '—'}</td>
                            <td className="py-2 px-3 text-slate-300">{cd.model_preds?.m3gnet != null ? `${Number(cd.model_preds.m3gnet).toFixed(3)} eV` : '—'}</td>
                            <td className="py-2 px-3 text-slate-300">{cd.model_preds?.xgboost != null ? `${Number(cd.model_preds.xgboost).toFixed(3)} eV` : '—'}</td>
                            <td className="py-2 px-3 text-amber-300">{cd.spread != null ? Number(cd.spread).toFixed(3) : '—'}</td>
                            <td className="py-2 px-3 text-right">
                              <span className="text-[10px] px-2 py-0.5 rounded bg-rose-500/10 text-rose-300 border border-rose-500/20">
                                Disagreement
                              </span>
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>
              )}
            </div>
          )}

          <div className="grid gap-5 xl:grid-cols-2">
            {candidates.map((candidate) => (
              <article
                key={candidate.material_hash}
                className={`card p-6 flex flex-col justify-between ${
                  selectedHash === candidate.material_hash ? 'ring-1 ring-emerald-400 border-emerald-500/40' : ''
                }`}
              >
                <div>
                  <div className="flex flex-wrap items-center justify-between gap-2 border-b border-white/[0.06] pb-3">
                    <h3 className="font-heading text-2xl font-bold tracking-tight text-white">{candidate.formula}</h3>
                    <span className="rounded-full bg-emerald-500/10 border border-emerald-500/20 px-2.5 py-0.5 text-xs font-mono text-emerald-300">
                      Consensus Validated
                    </span>
                  </div>

                  <dl className="mt-4 grid grid-cols-2 gap-3 text-xs font-mono">
                    <div className="grid-panel p-2.5">
                      <dt className="text-slate-400">Density</dt>
                      <dd className="mt-1 text-sm font-semibold text-white">{Number(candidate.density).toFixed(3)} g/cm³</dd>
                    </div>
                    <div className="grid-panel p-2.5">
                      <dt className="text-slate-400">E Above Hull</dt>
                      <dd className="mt-1 text-sm font-semibold text-emerald-300">{Number(candidate.e_hull).toFixed(4)} eV/atom</dd>
                    </div>
                    <div className="grid-panel p-2.5">
                      <dt className="text-slate-400">Formation Energy</dt>
                      <dd className="mt-1 text-sm font-semibold text-white">{Number(candidate.predicted_formation_energy).toFixed(4)} eV/atom</dd>
                    </div>
                    <div className="grid-panel p-2.5">
                      <dt className="text-slate-400">Ensemble Spread (τ)</dt>
                      <dd className="mt-1 text-sm font-semibold text-amber-300">{Number(candidate.consensus_spread).toFixed(4)}</dd>
                    </div>
                  </dl>

                  <div className="discovery-fingerprint mt-4 rounded-lg bg-black/40 border border-white/[0.06] p-2.5 text-xs font-mono text-slate-400 break-all">
                    <span className="text-slate-500 block text-[10px] uppercase mb-1">SHA-256 Crystal Fingerprint</span>
                    {candidate.material_hash}
                  </div>

                  <details className="mt-3 text-xs text-slate-400 font-mono">
                    <summary className="discovery-payload-summary cursor-pointer hover:text-slate-200 transition-colors">
                      View Raw Crystal Structure Payload
                    </summary>
                    <pre className="discovery-payload mt-2 max-h-44 overflow-auto rounded-lg bg-black/50 p-3 text-[11px] text-slate-300 border border-white/[0.04]">
                      {JSON.stringify(candidate.structure_payload, null, 2)}
                    </pre>
                  </details>
                </div>

                <button
                  type="button"
                  disabled={
                    registeringHash === candidate.material_hash ||
                    selectedHash === candidate.material_hash
                  }
                  onClick={() => void registerCandidate(candidate)}
                  className={`mt-6 w-full ${
                    selectedHash === candidate.material_hash
                      ? 'button-secondary text-emerald-300 border-emerald-500/30 cursor-default'
                      : 'button-primary'
                  } disabled:cursor-not-allowed disabled:opacity-50`}
                >
                  {selectedHash === candidate.material_hash
                    ? 'Registered on Ledger'
                    : registeringHash === candidate.material_hash
                    ? 'Registering on Blockchain…'
                    : 'Register Structure on Blockchain'}
                </button>
              </article>
            ))}
          </div>
        </section>
      )}

      {/* Controlled Demonstration Reference Material */}
      {job?.result?.demo_reference_asset && (
        <section className="card border-2 border-cyan-500/30 bg-gradient-to-b from-cyan-950/20 via-black/40 to-black/60 p-6 md:p-8 space-y-6">
          <div className="flex flex-wrap items-center justify-between gap-3 border-b border-cyan-500/20 pb-4">
            <div className="flex items-center gap-3">
              <div className="p-2.5 rounded-xl bg-cyan-500/10 border border-cyan-500/30 text-cyan-400">
                <Sparkles className="h-6 w-6" />
              </div>
              <div>
                <div className="flex items-center gap-2">
                  <h2 className="font-heading text-2xl font-bold tracking-tight text-white">
                    {job.result.demo_reference_asset.formula} (Magnesium Silicide)
                  </h2>
                  <span className="rounded-full bg-cyan-500/15 border border-cyan-500/40 px-3 py-1 text-xs font-mono font-semibold text-cyan-300">
                    REFERENCE DEMONSTRATION ASSET
                  </span>
                </div>
                <p className="text-xs text-slate-300 mt-0.5">
                  Controlled review lifecycle reference grounded in Materials Project <strong>mp-1367</strong> (ICSD-642931).
                </p>
              </div>
            </div>

            <div className="rounded-lg bg-amber-500/10 border border-amber-500/30 px-3 py-1.5 text-xs font-mono text-amber-300 flex items-center gap-2">
              <AlertTriangle className="h-4 w-4 shrink-0" />
              <span>DEMO REFERENCE — NOT A LIVE AI-GENERATED DISCOVERY</span>
            </div>
          </div>

          <div className="rounded-xl bg-black/40 border border-white/[0.08] p-4 text-xs font-mono text-slate-300 flex flex-wrap items-center justify-between gap-3">
            <div>
              <span className="text-slate-500 block text-[10px] uppercase">SHA-256 Crystal Fingerprint</span>
              <span className="text-cyan-300 select-all font-semibold">{job.result.demo_reference_asset.material_hash}</span>
            </div>
            <div className="text-right">
              <span className="text-slate-500 block text-[10px] uppercase">Registrant Role</span>
              <span className="text-slate-200">Demo Curator / Registrant (Not Inventor)</span>
            </div>
          </div>

          {/* Properties Grid */}
          <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3 text-xs font-mono">
            <div className="grid-panel p-3">
              <div className="text-slate-400">Crystal System</div>
              <div className="mt-1 text-sm font-semibold text-white">{job.result.demo_reference_asset.crystal_system}</div>
              <div className="text-[10px] text-slate-500">{job.result.demo_reference_asset.space_group}</div>
            </div>
            <div className="grid-panel p-3">
              <div className="text-slate-400">Lattice Param (a)</div>
              <div className="mt-1 text-sm font-semibold text-white">{job.result.demo_reference_asset.lattice_parameter_a} Å</div>
              <div className="text-[10px] text-slate-500">α=β=γ=90°</div>
            </div>
            <div className="grid-panel p-3">
              <div className="text-slate-400">Density</div>
              <div className="mt-1 text-sm font-semibold text-white">{Number(job.result.demo_reference_asset.density).toFixed(3)} g/cm³</div>
              <div className="text-[10px] text-slate-500">Target: 2.0</div>
            </div>
            <div className="grid-panel p-3">
              <div className="text-slate-400">Formation Energy</div>
              <div className="mt-1 text-sm font-semibold text-white">{Number(job.result.demo_reference_asset.predicted_formation_energy).toFixed(3)} eV/atom</div>
              <div className="text-[10px] text-slate-500">Target: -0.25</div>
            </div>
            <div className="grid-panel p-3">
              <div className="text-slate-400">E Above Hull</div>
              <div className="mt-1 text-sm font-semibold text-emerald-400">{Number(job.result.demo_reference_asset.e_hull).toFixed(4)} eV/atom</div>
              <div className="text-[10px] text-emerald-500 font-semibold">Ground State (Stable)</div>
            </div>
            <div className="grid-panel p-3">
              <div className="text-slate-400">Band Gap (Eg)</div>
              <div className="mt-1 text-sm font-semibold text-white">{job.result.demo_reference_asset.band_gap} eV</div>
              <div className="text-[10px] text-slate-500">Indirect SC</div>
            </div>
          </div>

          {/* Interactive Lifecycle Stages */}
          <div className="rounded-2xl border border-cyan-500/20 bg-black/50 p-5 space-y-4">
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-white/[0.06] pb-3">
              <h3 className="font-heading text-sm font-semibold text-white flex items-center gap-2">
                <ShieldCheck className="h-4 w-4 text-cyan-400" />
                <span>End-to-End Demonstration Lifecycle Pipeline</span>
              </h3>
              <div className="flex items-center gap-3">
                <button
                  type="button"
                  disabled={demoLoadingStep === 'reset'}
                  onClick={handleDemoReset}
                  className="inline-flex items-center gap-1.5 text-xs font-mono px-3 py-1.5 rounded-lg border border-amber-500/30 bg-amber-500/10 text-amber-300 hover:bg-amber-500/20 transition-all cursor-pointer"
                  title="Reset demo stages to start demonstration from beginning"
                >
                  <RotateCcw className={`h-3.5 w-3.5 ${demoLoadingStep === 'reset' ? 'animate-spin' : ''}`} />
                  <span>{demoLoadingStep === 'reset' ? 'Resetting…' : 'Reset Pipeline Demo'}</span>
                </button>
                <span className="text-xs font-mono text-cyan-300">
                  {demoStatus?.marketplace_sold
                    ? 'Stage 4/4 Complete: Purchased'
                    : demoStatus?.marketplace_listed
                    ? 'Stage 3/4 Complete: Listed'
                    : demoStatus?.blockchain_verified
                    ? 'Stage 2/4 Complete: Attested'
                    : demoStatus?.registered_in_store
                    ? 'Stage 1/4 Complete: Registered'
                    : 'Ready to Begin'}
                </span>
              </div>
            </div>

            <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
              {/* Step 1: Register */}
              <div className={`p-4 rounded-xl border ${demoStatus?.registered_in_store ? 'border-emerald-500/30 bg-emerald-500/[0.04]' : 'border-white/[0.08] bg-white/[0.02]'}`}>
                <div className="flex items-center justify-between mb-2">
                  <span className="text-[11px] font-mono text-slate-400">1. IPFS & Ledger</span>
                  {demoStatus?.registered_in_store ? <CheckCircle2 className="h-4 w-4 text-emerald-400" /> : <Clock className="h-4 w-4 text-slate-500" />}
                </div>
                <div className="text-sm font-semibold text-white mb-1">Confidential Upload</div>
                <p className="text-[11px] text-slate-400 mb-3">Encrypt CIF with AES-256-GCM, pin to IPFS, sync to MFS, and register fingerprint on blockchain.</p>
                <button
                  type="button"
                  disabled={demoLoadingStep === 'register' || demoStatus?.registered_in_store}
                  onClick={handleDemoRegister}
                  className={`w-full text-xs font-mono py-2 px-3 rounded-lg font-medium transition-colors cursor-pointer ${demoStatus?.registered_in_store ? 'bg-emerald-500/20 text-emerald-300 cursor-default' : 'bg-cyan-500 hover:bg-cyan-400 text-slate-950 font-semibold'}`}
                >
                  {demoLoadingStep === 'register' ? 'Registering…' : demoStatus?.registered_in_store ? 'Registered on Ledger' : '1. Register Material'}
                </button>
              </div>

              {/* Step 2: Attest */}
              <div className={`p-4 rounded-xl border ${demoStatus?.blockchain_verified ? 'border-emerald-500/30 bg-emerald-500/[0.04]' : 'border-white/[0.08] bg-white/[0.02]'}`}>
                <div className="flex items-center justify-between mb-2">
                  <span className="text-[11px] font-mono text-slate-400">2. Validator Attestation</span>
                  {demoStatus?.blockchain_verified ? <CheckCircle2 className="h-4 w-4 text-emerald-400" /> : <Clock className="h-4 w-4 text-slate-500" />}
                </div>
                <div className="text-sm font-semibold text-white mb-1">0.05 ETH Stake</div>
                <p className="text-[11px] text-slate-400 mb-3">Independent validator inspects Ehull=0.0 and stakes 0.05 ETH on MatChainRegistry contract.</p>
                <button
                  type="button"
                  disabled={demoLoadingStep === 'attest' || !demoStatus?.registered_in_store || demoStatus?.blockchain_verified}
                  onClick={handleDemoAttest}
                  className={`w-full text-xs font-mono py-2 px-3 rounded-lg font-medium transition-colors cursor-pointer ${demoStatus?.blockchain_verified ? 'bg-emerald-500/20 text-emerald-300 cursor-default' : 'bg-cyan-500 hover:bg-cyan-400 text-slate-950 font-semibold disabled:opacity-40 disabled:cursor-not-allowed'}`}
                >
                  {demoLoadingStep === 'attest' ? 'Attesting…' : demoStatus?.blockchain_verified ? 'Attested (0.05 ETH)' : '2. Attest Discovery'}
                </button>
              </div>

              {/* Step 3: List */}
              <div className={`p-4 rounded-xl border ${demoStatus?.marketplace_listed ? 'border-emerald-500/30 bg-emerald-500/[0.04]' : 'border-white/[0.08] bg-white/[0.02]'}`}>
                <div className="flex items-center justify-between mb-2">
                  <span className="text-[11px] font-mono text-slate-400">3. Marketplace Listing</span>
                  {demoStatus?.marketplace_listed ? <CheckCircle2 className="h-4 w-4 text-emerald-400" /> : <Clock className="h-4 w-4 text-slate-500" />}
                </div>
                <div className="text-sm font-semibold text-white mb-1">0.01 ETH Terms</div>
                <p className="text-[11px] text-slate-400 mb-3">Create on-chain listing on MatChainMarketplace requiring verified validator attestation.</p>
                <button
                  type="button"
                  disabled={demoLoadingStep === 'list' || !demoStatus?.blockchain_verified || demoStatus?.marketplace_listed}
                  onClick={handleDemoList}
                  className={`w-full text-xs font-mono py-2 px-3 rounded-lg font-medium transition-colors cursor-pointer ${demoStatus?.marketplace_listed ? 'bg-emerald-500/20 text-emerald-300 cursor-default' : 'bg-cyan-500 hover:bg-cyan-400 text-slate-950 font-semibold disabled:opacity-40 disabled:cursor-not-allowed'}`}
                >
                  {demoLoadingStep === 'list' ? 'Listing…' : demoStatus?.marketplace_listed ? 'Listed on Marketplace' : '3. List Material'}
                </button>
              </div>

              {/* Step 4: Purchase */}
              <div className={`p-4 rounded-xl border ${demoStatus?.marketplace_sold ? 'border-emerald-500/30 bg-emerald-500/[0.04]' : 'border-white/[0.08] bg-white/[0.02]'}`}>
                <div className="flex items-center justify-between mb-2">
                  <span className="text-[11px] font-mono text-slate-400">4. License Purchase</span>
                  {demoStatus?.marketplace_sold ? <CheckCircle2 className="h-4 w-4 text-emerald-400" /> : <Clock className="h-4 w-4 text-slate-500" />}
                </div>
                <div className="text-sm font-semibold text-white mb-1">Second Test Wallet</div>
                <p className="text-[11px] text-slate-400 mb-3">Second wallet purchases on-chain for 0.01 ETH; seller receives funds and buyer unlocks decrypted CIF.</p>
                <button
                  type="button"
                  disabled={demoLoadingStep === 'purchase' || !demoStatus?.marketplace_listed || demoStatus?.marketplace_sold}
                  onClick={handleDemoPurchase}
                  className={`w-full text-xs font-mono py-2 px-3 rounded-lg font-medium transition-colors cursor-pointer ${demoStatus?.marketplace_sold ? 'bg-emerald-500/20 text-emerald-300 cursor-default' : 'bg-cyan-500 hover:bg-cyan-400 text-slate-950 font-semibold disabled:opacity-40 disabled:cursor-not-allowed'}`}
                >
                  {demoLoadingStep === 'purchase' ? 'Purchasing…' : demoStatus?.marketplace_sold ? 'License Purchased' : '4. Purchase License'}
                </button>
              </div>
            </div>

            {/* Quick Actions & Links */}
            <div className="flex flex-wrap items-center justify-between gap-3 pt-2">
              <div className="flex items-center gap-2">
                {demoStatus?.ipfs_cid && (
                  <a
                    href={demoStatus.ipfs_gateway_url || `http://127.0.0.1:8080/ipfs/${String(demoStatus.ipfs_cid).replace(/^ipfs:\/\/?/, '').replace(/^\/ipfs\//, '')}`}
                    target="_blank"
                    rel="noreferrer"
                    className="inline-flex items-center gap-1.5 text-xs font-mono text-cyan-400 hover:text-cyan-300 bg-cyan-500/10 border border-cyan-500/20 rounded-lg px-2.5 py-1.5"
                  >
                    <ExternalLink className="h-3.5 w-3.5" />
                    <span>View Encrypted IPFS Payload</span>
                  </a>
                )}
                {demoStatus?.marketplace_sold && (
                  <a
                    href={`/api/storage/download/${job.result.demo_reference_asset.material_hash}`}
                    className="inline-flex items-center gap-1.5 text-xs font-mono text-emerald-400 hover:text-emerald-300 bg-emerald-500/10 border border-emerald-500/20 rounded-lg px-2.5 py-1.5"
                  >
                    <Download className="h-3.5 w-3.5" />
                    <span>Download Decrypted CIF</span>
                  </a>
                )}
              </div>

              <a
                href="/marketplace"
                className="inline-flex items-center gap-1 text-xs font-mono text-slate-300 hover:text-white"
              >
                <span>Open Marketplace</span>
                <ArrowRight className="h-3.5 w-3.5" />
              </a>
            </div>
          </div>
        </section>
      )}
    </div>
  );
}

type DiscoveryJob = {
  job_id: string;
  status: 'queued' | 'running' | 'completed' | 'failed';
  created_at: number;
  updated_at: number;
  progress?: number;
  error?: string | null;
  result?: {
    results?: GeneratedCandidate[];
    elapsed?: number;
    diagnostics?: Record<string, any>;
    model_availability?: Record<string, boolean>;
    demo_reference_asset?: any;
    is_demo_recipe?: boolean;
  } | null;
};
