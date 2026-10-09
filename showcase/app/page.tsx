import Link from "next/link";
import {
  ArrowUpRight,
  Play,
  Layers3,
  GitBranch,
  Database,
  Radio,
  Terminal,
  BookOpen,
  Check,
} from "lucide-react";
import { repository } from "../lib/labels";
export default function Home() {
  return (
    <main id="main">
      <section className="hero">
        <div className="hero-copy">
          <h1>
            InsightAgent<span>看见执行，复核依据。</span>
          </h1>
          <p>
            可视化、可解释、工具驱动的 AI Agent 工作台。
            <br className="desktop-break" />
            从知识检索到工具调用，让回答背后的执行记录清晰可查。
          </p>
          <div className="hero-actions">
            <Link className="button primary" href="/demo/">
              <Play size={17} fill="currentColor" />
              体验案例回放
            </Link>
            <a
              className="text-link"
              href={repository}
              target="_blank"
              rel="noopener noreferrer"
            >
              查看 GitHub 源码
              <ArrowUpRight size={17} />
            </a>
          </div>
        </div>
        <figure className="product-shot">
          <div className="shot-heading">
            <span>
              <span className="status-dot" />
              完整工作台
            </span>
            <span>Execution Trace / 知识检索与计算</span>
          </div>
          {/* A real screenshot of the existing workbench with dedicated public fixture data. */}
          {/* eslint-disable-next-line @next/next/no-img-element */}
          <img
            src="/workbench.png"
            alt="InsightAgent 工作台：合成预算问题、回答、工具执行记录与引用来源"
            width={1600}
            height={980}
            fetchPriority="high"
          />
          <figcaption>
            现有工作台实拍，使用专用合成案例。在线体验提供记录回放，完整应用可在本地运行。
          </figcaption>
        </figure>
      </section>
      <section className="section capabilities">
        <div className="section-heading">
          <span className="section-number">01 / 能力</span>
          <h2>
            回答之外，
            <br />
            还有完整的执行证据。
          </h2>
        </div>
        <div className="capability-list">
          <article>
            <Layers3 />
            <div>
              <h3>Execution Trace</h3>
              <p>
                时间线与流程图连接任务规划、工具输入输出和最终回答。展开节点，核对实际执行。
              </p>
            </div>
          </article>
          <article>
            <BookOpen />
            <div>
              <h3>Memory / RAG</h3>
              <p>
                会话记忆与知识库分工明确。检索保留来源和文档版本，知识导入支持后台处理。
              </p>
            </div>
          </article>
          <article>
            <GitBranch />
            <div>
              <h3>历史与分支恢复</h3>
              <p>
                查询执行历史、导出记录，编辑输入创建独立分支。原任务的失败证据继续保留。
              </p>
            </div>
          </article>
        </div>
      </section>
      <section className="section architecture">
        <div className="section-heading">
          <span className="section-number">02 / 架构</span>
          <h2>
            界面、执行与存储，
            <br />
            各有清晰边界。
          </h2>
        </div>
        <div className="architecture-content">
          <div
            className="architecture-diagram"
            aria-label="Next.js 通过 REST 和 SSE 访问 FastAPI；后端调用模型、PostgreSQL 和 Chroma"
          >
            <div className="arch-node">
              <Layers3 />
              <strong>Next.js</strong>
              <span>工作台 · Trace</span>
            </div>
            <div className="arch-connector">REST / SSE</div>
            <div className="arch-node">
              <Terminal />
              <strong>FastAPI</strong>
              <span>规划 · 工具 · worker</span>
            </div>
            <div className="arch-branches">
              <div>
                <Radio />
                <strong>模型 API</strong>
                <span>规划 / 流式回答</span>
              </div>
              <div>
                <Database />
                <strong>PostgreSQL</strong>
                <span>业务历史 / 执行账本</span>
              </div>
              <div>
                <Database />
                <strong>Chroma</strong>
                <span>Memory / RAG 向量</span>
              </div>
            </div>
          </div>
          <p className="architecture-note">
            这是完整应用的架构。当前展示站独立静态运行，不连接后端、数据库或模型
            API。
          </p>
        </div>
      </section>
      <section className="section engineering">
        <div className="section-heading">
          <span className="section-number">03 / 工程</span>
          <h2>可展示，也可核查。</h2>
        </div>
        <div className="engineering-list">
          <article>
            <span>01</span>
            <div>
              <h3>实时流与增量同步</h3>
              <p>
                SSE 携带任务、步骤标识与 heartbeat；HTTP
                增量查询补齐历史记录，前端按 ID 与序号合并。
              </p>
            </div>
          </article>
          <article>
            <span>02</span>
            <div>
              <h3>有界执行与恢复</h3>
              <p>
                规划、工具和反馈共享执行契约；轮次、队列、取消与超时都有边界。分支重跑保留父子关系。
              </p>
            </div>
          </article>
          <article>
            <span>03</span>
            <div>
              <h3>契约与回归验证</h3>
              <p>
                OpenAPI
                指纹、模块回归和跨浏览器检查各有证据。模型替身、真实模型与部署验证分别记录。
              </p>
            </div>
          </article>
        </div>
      </section>
      <section className="closing">
        <div>
          <span className="section-number">从一次执行开始</span>
          <h2>打开案例，亲自展开 Trace。</h2>
          <p>
            无需登录，无需 API
            Key。两个预设案例，分别展示成功执行与失败后的独立分支恢复。
          </p>
          <Link className="button primary" href="/demo/">
            <Play size={17} fill="currentColor" />
            进入案例体验
          </Link>
        </div>
        <aside>
          <h3>
            <Check size={18} />
            展示与验证边界
          </h3>
          <p>
            真实模型执行与受控失败 fixture 分别标注。Trace
            是执行依据，不保证每句回答正确；未知用量不补零。
          </p>
          <p>本地工程已完成。外部业务签收与完整应用部署尚未验收。</p>
          <a
            className="text-link"
            href={`${repository}/blob/main/docs/acceptance.md`}
            target="_blank"
            rel="noopener noreferrer"
          >
            查看验收记录
            <ArrowUpRight size={16} />
          </a>
        </aside>
      </section>
    </main>
  );
}
