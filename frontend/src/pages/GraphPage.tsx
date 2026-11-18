import React from 'react';
import { useParams } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import ReactFlow, {
  Controls,
  Background,
  BackgroundVariant,
  useNodesState,
  useEdgesState,
} from 'reactflow';
import 'reactflow/dist/style.css';
import { api } from '../api/endpoints';
import { LoadingSpinner } from '../components/common/LoadingSpinner';
import { Network, AlertTriangle } from 'lucide-react';

export const GraphPage: React.FC = () => {
  const { id: repoId } = useParams<{ id: string }>();

  const { data: graphData, isLoading } = useQuery({
    queryKey: ['dependencyGraph', repoId],
    queryFn: async () => (await api.analytics.getGraph(repoId!)).data,
    enabled: !!repoId,
  });

  const [nodes, setNodes, onNodesChange] = useNodesState([]);
  const [edges, setEdges, onEdgesChange] = useEdgesState([]);

  React.useEffect(() => {
    if (graphData) {
      setNodes(graphData.nodes || []);
      setEdges(graphData.edges || []);
    }
  }, [graphData, setNodes, setEdges]);

  if (isLoading) return <LoadingSpinner text="Computing dependency graph layout..." />;

  const circularCount = graphData?.metrics?.circular_count || 0;

  return (
    <div className="space-y-4 animate-fade-in">
      <div className="flex items-center justify-between pb-4 border-b border-dark-800">
        <div>
          <h1 className="text-2xl font-bold text-white tracking-tight flex items-center gap-2">
            <Network className="w-6 h-6 text-brand-400" />
            Dependency Architecture Graph
          </h1>
          <p className="text-sm text-slate-400 mt-1">
            Interactive NetworkX layout displaying file imports and circular dependency cycles.
          </p>
        </div>

        {circularCount > 0 ? (
          <div className="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-rose-500/15 border border-rose-500/30 text-rose-300 text-xs font-semibold">
            <AlertTriangle className="w-4 h-4 text-rose-400" />
            {circularCount} Circular Dependency Groups Detected
          </div>
        ) : (
          <div className="text-xs text-emerald-400 bg-emerald-500/10 border border-emerald-500/30 px-3 py-1.5 rounded-lg font-semibold">
            No Circular Dependencies Detected
          </div>
        )}
      </div>

      {/* React Flow Viewport */}
      <div className="h-[calc(100vh-220px)] border border-dark-800 rounded-xl overflow-hidden bg-dark-950">
        <ReactFlow
          nodes={nodes}
          edges={edges}
          onNodesChange={onNodesChange}
          onEdgesChange={onEdgesChange}
          fitView
        >
          <Background variant={BackgroundVariant.Dots} gap={16} size={1} color="#1e293b" />
          <Controls />
        </ReactFlow>
      </div>
    </div>
  );
};
