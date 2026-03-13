// Vue 应用
const { createApp, ref, computed, onMounted, nextTick } = Vue;

createApp({
    setup() {
        // 状态
        const isConnected = ref(false);
        const logs = ref([]);
        const logFilter = ref('');
        const agents = ref([]);
        const connections = ref([]);
        const selectedAgent = ref(null);
        const logContainer = ref(null);
        const asyncState = ref({
            all_tasks_count: 0,
            current_task: null,
            all_tasks: [],
            event_loop: null
        });
        const recentFlows = ref([]);

        // 当前布局类型
        let currentLayoutType = 'cose';

        // 适应视图
        function fitTopology() {
            if (cytoscapeInstance) {
                cytoscapeInstance.fit();
                cytoscapeInstance.center();
            }
        }

        // 重新运行布局
        function resetLayout() {
            if (!cytoscapeInstance) return;

            const layout = cytoscapeInstance.layout({
                name: 'cose',
                fit: true,
                padding: 50,
                animate: true,
                animationDuration: 500,
                componentSpacing: 200,
                nodeRepulsion: 800000,
                edgeElasticity: 50,
                nestingFactor: 10,
                gravity: 40,
                numIter: 2000,
                initialTemp: 400,
                coolingFactor: 0.92,
                minTemp: 1.0,
                nodeOverlap: 40,
                idealEdgeLength: 150
            });
            layout.run();
        }

        // 切换布局类型
        function toggleLayout() {
            if (!cytoscapeInstance) return;

            const layouts = ['cose', 'circle', 'grid', 'concentric'];
            const currentIndex = layouts.indexOf(currentLayoutType);
            currentLayoutType = layouts[(currentIndex + 1) % layouts.length];

            const layoutOptions = {
                name: currentLayoutType,
                fit: true,
                padding: 30,
                animate: true,
                animationDuration: 500
            };

            // 为力导向布局添加特殊参数
            if (currentLayoutType === 'cose') {
                Object.assign(layoutOptions, {
                    padding: 50,
                    componentSpacing: 200,
                    nodeRepulsion: 800000,
                    edgeElasticity: 50,
                    nestingFactor: 10,
                    gravity: 40,
                    numIter: 2000,
                    nodeOverlap: 40,
                    idealEdgeLength: 150
                });
            }

            // 为同心圆布局添加参数
            if (currentLayoutType === 'concentric') {
                Object.assign(layoutOptions, {
                    minNodeSpacing: 50,
                    levelWidth: function(nodes) {
                        return nodes.degree() / 2;
                    }
                });
            }

            const layout = cytoscapeInstance.layout(layoutOptions);
            layout.run();

            // 显示提示
            console.log('Switched to layout:', currentLayoutType);
        }

        // 连接 WebSocket
        function connectWebSocket() {
            const wsUrl = `ws://${window.location.host}`;
            ws = new WebSocket(wsUrl);

            ws.onopen = () => {
                isConnected.value = true;
                console.log('Connected to server');
            };

            ws.onclose = () => {
                isConnected.value = false;
                console.log('Disconnected from server');
                // 尝试重连
                setTimeout(connectWebSocket, 3000);
            };

            ws.onerror = (error) => {
                console.error('WebSocket error:', error);
            };

            ws.onmessage = (event) => {
                try {
                    const data = JSON.parse(event.data);
                    console.log('[WebSocket] Received message:', data.type, data);
                    handleMessage(data);
                } catch (err) {
                    console.error('[WebSocket] Error parsing message:', err);
                }
            };
        }

        // 处理 WebSocket 消息
        function handleMessage(data) {
            const type = data.type;

            if (type === 'init') {
                // 初始数据
                console.log('Received init message:', data);
                if (data.topology) {
                    agents.value = data.topology.agents || [];
                    connections.value = data.topology.connections || [];
                    console.log('Set agents:', agents.value.length, 'connections:', connections.value.length);
                    updateCytoscape();
                } else {
                    console.log('No topology in init message');
                }
                if (data.stats) {
                    console.log('Stats:', data.stats);
                }
                if (data.async_state) {
                    asyncState.value = data.async_state;
                }
                if (data.recent_flows) {
                    recentFlows.value = data.recent_flows;
                }
            } else if (type === 'topology' || type === 'topology_update') {
                // 拓扑更新
                console.log('[WebSocket] Received topology_update:', data);
                if (data.topology) {
                    const oldConnectionCount = connections.value.length;
                    const oldAgentCount = agents.value.length;

                    console.log('[WebSocket] Setting agents:', data.topology.agents?.length, 'connections:', data.topology.connections?.length);
                    agents.value = data.topology.agents || [];
                    connections.value = data.topology.connections || [];

                    const newConnectionCount = connections.value.length;
                    const newAgentCount = agents.value.length;

                    console.log('[WebSocket] Updated connections:', connections.value.map(c => ({from: c.from, to: c.to, keyword: c.keyword, type: c.type})));

                    // 判断更新类型：如果节点数和连接数都不变，只是 keyword 更新
                    const isKeywordUpdate = (oldAgentCount === newAgentCount) && (oldConnectionCount === newConnectionCount) && (oldConnectionCount > 0);
                    console.log('[WebSocket] Update type:', isKeywordUpdate ? 'keyword update' : 'structural update');

                    // 使用 nextTick 确保 Vue 更新后再渲染
                    nextTick(() => {
                        updateCytoscape(isKeywordUpdate);
                    });
                } else {
                    console.warn('[WebSocket] topology_update missing topology data');
                }
            } else if (type === 'log_entry') {
                // 新日志条目
                logs.value.push(data.entry);
                if (logs.value.length > 500) {
                    logs.value = logs.value.slice(-500);
                }
                nextTick(() => {
                    if (logContainer.value) {
                        logContainer.value.scrollTop = logContainer.value.scrollHeight;
                    }
                });
            } else if (type === 'agent') {
                // Agent 详情
                if (data.data) {
                    selectedAgent.value = data.data;
                }
            } else if (type === 'message_flow') {
                // 消息流更新 - 触发边动画
                handleMessageFlow(data.entry);
                if (data.recent_flows) {
                    recentFlows.value = data.recent_flows;
                }
            } else if (type === 'agent_activated') {
                // Agent 激活 - 高亮节点
                handleAgentActivated(data.entry);
                if (data.agent) {
                    // 更新 agents 列表中的激活计数
                    const idx = agents.value.findIndex(a => a.id === data.agent.id);
                    if (idx !== -1) {
                        agents.value[idx] = data.agent;
                    }
                }
            } else if (type === 'async_update') {
                // 异步状态更新
                if (data.async_state) {
                    asyncState.value = data.async_state;
                }
            }
        }

        // 处理消息流 - 高亮边
        function handleMessageFlow(entry) {
            if (!cytoscapeInstance || !entry) return;

            const data = entry.data || {};
            const from = data.source_agent || data.sender_id;
            const to = data.target_agent || data.receiver_id;

            if (from && to) {
                // 找到对应的输出边（消息发送方向）并高亮
                const edge = cytoscapeInstance.edges().filter(e =>
                    e.data('source') === from && e.data('target') === to && e.hasClass('output-edge')
                );

                if (edge.length > 0) {
                    // 添加流动动画
                    edge.animate({
                        style: {
                            'line-color': '#f472b6',
                            'target-arrow-color': '#f472b6',
                            'width': 4
                        }
                    }, {
                        duration: 200
                    }).animate({
                        style: {
                            'line-color': '#3b82f6',
                            'target-arrow-color': '#3b82f6',
                            'width': 2.5
                        }
                    }, {
                        duration: 300
                    });
                }
            }
        }

        // 处理 Agent 激活 - 高亮节点
        function handleAgentActivated(entry) {
            if (!cytoscapeInstance || !entry) return;

            const data = entry.data || {};
            const agentId = data.agent_id;

            if (agentId) {
                const node = cytoscapeInstance.getElementById(agentId);
                if (node) {
                    // 高亮节点（只闪烁边框，不改变背景色和大小）
                    node.animate({
                        style: {
                            'border-width': 5,
                            'border-color': '#4ade80'
                        }
                    }, {
                        duration: 200
                    }).animate({
                        style: {
                            'border-width': 0,
                            'border-color': '#fff'
                        }
                    }, {
                        duration: 500
                    });
                }
            }
        }

        // Cytoscape 拓扑图
        function initCytoscape() {
            const container = document.getElementById('cytoplasm');
            if (!container) {
                console.error('Cytoscape container not found!');
                return;
            }
            console.log('Initializing Cytoscape...');

            cytoscapeInstance = cytoscape({
                container: container,
                style: [
                    {
                        selector: 'node',
                        style: {
                            'background-color': '#60a5fa',
                            'label': 'data(label)',
                            'text-valign': 'center',
                            'text-halign': 'center',
                            'color': '#fff',
                            'text-outline-color': '#1e293b',
                            'text-outline-width': 2,
                            'width': 70,
                            'height': 70,
                            'font-size': '10px',
                            'font-weight': 'bold',
                            'border-width': 0,
                            'border-color': '#fff',
                            'transition-property': 'border-width, border-color, opacity',
                            'transition-duration': '0.2s'
                        }
                    },
                    {
                        selector: 'node[type="Agent"]',
                        style: {
                            'background-color': '#60a5fa'
                        }
                    },
                    {
                        selector: 'node[type="InputAgent"]',
                        style: {
                            'background-color': '#4ade80',
                            'shape': 'round-rectangle'
                        }
                    },
                    {
                        selector: 'node[type="OutputAgent"]',
                        style: {
                            'background-color': '#f472b6',
                            'shape': 'round-rectangle'
                        }
                    },
                    {
                        selector: 'edge',
                        style: {
                            'width': 2,
                            'line-color': '#475569',
                            'target-arrow-color': '#475569',
                            'target-arrow-shape': 'triangle',
                            'curve-style': 'unbundled-bezier',
                            'control-point-step-size': 40,
                            'label': 'data(keyword)',
                            'font-size': '8px',
                            'color': '#94a3b8',
                            'text-background-color': '#0f172a',
                            'text-background-opacity': 0.8,
                            'text-background-padding': '2px',
                            'text-background-shape': 'roundrectangle',
                            'text-rotation': 'autorotate',
                            'text-margin-y': -10,
                            'arrow-scale': 1.2
                        }
                    },
                    {
                        selector: '.input-edge',
                        style: {
                            'width': 1.5,
                            'line-color': '#9ca3af',  // 浅灰色
                            'line-style': 'dashed',    // 虚线
                            'target-arrow-shape': 'none',  // 输入连接无箭头
                            'curve-style': 'unbundled-bezier',
                            'control-point-step-size': 80,  // 更大的弯曲，让边向外分开
                            'label': 'data(keyword)',
                            'font-size': '7px',
                            'color': '#9ca3af',
                            'text-opacity': 0.6,  // 文本透明度
                            'text-background-color': '#0f172a',
                            'text-background-opacity': 0.6,  // 背景透明度
                            'text-background-padding': '2px',
                            'text-background-shape': 'roundrectangle',
                            'text-rotation': 'autorotate',
                            'text-margin-y': -10,
                            'opacity': 0.6  // 边线透明度
                        }
                    },
                    {
                        selector: '.output-edge',
                        style: {
                            'width': 2.5,
                            'line-color': '#3b82f6',   // 更深的蓝色
                            'line-style': 'solid',     // 实线
                            'target-arrow-color': '#3b82f6',
                            'target-arrow-shape': 'triangle',
                            'curve-style': 'unbundled-bezier',
                            'control-point-step-size': 30,  // 较小的弯曲，让边向内
                            'label': 'data(keyword)',
                            'font-size': '9px',
                            'color': '#60a5fa',
                            'text-background-color': '#0f172a',
                            'text-background-opacity': 0.8,
                            'text-background-padding': '2px',
                            'text-background-shape': 'roundrectangle',
                            'text-rotation': 'autorotate',
                            'text-margin-y': -10,
                            'arrow-scale': 1.3
                        }
                    },
                    {
                        selector: 'node:selected',
                        style: {
                            'background-color': '#fbbf24',
                            'border-width': 4,
                            'border-color': '#fff'
                        }
                    },
                    {
                        selector: '.highlighted',
                        style: {
                            'line-color': '#f472b6',
                            'target-arrow-color': '#f472b6',
                            'width': 4
                        }
                    }
                ],
                layout: {
                    name: 'grid',
                    fit: true,
                    padding: 10
                },
                // 启用交互
                userZoomingEnabled: true,
                userPanningEnabled: true,
                boxSelectionEnabled: true,
                selectionType: 'single',
                // 滚轮缩放灵敏度（数值越小缩放越精细）
                wheelSensitivity: 0.15,
                // 最小/最大缩放级别
                minZoom: 0.1,
                maxZoom: 3.0
            });

            // 点击节点事件
            cytoscapeInstance.on('tap', 'node', (event) => {
                const node = event.target;
                const agentId = node.data('id');
                selectAgentById(agentId);
            });

            // 鼠标悬停高亮相关连接
            cytoscapeInstance.on('mouseover', 'node', (event) => {
                const node = event.target;
                const connectedEdges = node.connectedEdges();
                const connectedNodes = node.neighborhood().nodes();

                // 降低其他元素透明度
                cytoscapeInstance.elements().not(node).not(connectedEdges).not(connectedNodes).animate({
                    style: { 'opacity': 0.2 }
                }, { duration: 200 });

                // 高亮当前节点（只改变边框，不改变大小）
                node.animate({
                    style: {
                        'border-width': 4,
                        'border-color': '#fbbf24',
                        'opacity': 1
                    }
                }, { duration: 200 });

                // 高亮输入边（灰色虚线变亮）
                connectedEdges.filter('.input-edge').animate({
                    style: {
                        'line-color': '#d1d5db',
                        'width': 2.5,
                        'opacity': 1  // 悬停时不透明
                    }
                }, { duration: 200 });

                // 高亮输出边（蓝色实线变亮）
                connectedEdges.filter('.output-edge').animate({
                    style: {
                        'line-color': '#93c5fd',
                        'target-arrow-color': '#93c5fd',
                        'width': 3.5,
                        'opacity': 1
                    }
                }, { duration: 200 });

                // 高亮连接的节点
                connectedNodes.animate({
                    style: { 'opacity': 1 }
                }, { duration: 200 });
            });

            // 鼠标移出恢复
            cytoscapeInstance.on('mouseout', 'node', () => {
                // 恢复节点样式（不修改width/height，避免覆盖动态大小）
                cytoscapeInstance.nodes().animate({
                    style: {
                        'opacity': 1,
                        'border-width': 0,
                        'border-color': '#fff'
                    }
                }, { duration: 200 });

                // 恢复输入边样式
                cytoscapeInstance.edges('.input-edge').animate({
                    style: {
                        'opacity': 0.6,  // 恢复半透明
                        'line-color': '#9ca3af',
                        'width': 1.5
                    }
                }, { duration: 200 });

                // 恢复输出边样式
                cytoscapeInstance.edges('.output-edge').animate({
                    style: {
                        'opacity': 1,
                        'line-color': '#3b82f6',
                        'target-arrow-color': '#3b82f6',
                        'width': 2.5
                    }
                }, { duration: 200 });
            });

            // 启用节点拖拽
            cytoscapeInstance.on('dragfree', 'node', (event) => {
                console.log('Node dragged:', event.target.data('id'));
            });

            console.log('Cytoscape initialized');
        }

        // 更新拓扑图
        function updateCytoscape(isKeywordUpdate = false) {
            if (!cytoscapeInstance) {
                initCytoscape();
            }

            // 如果没有节点，不更新
            if (agents.value.length === 0) {
                console.log('No agents to display');
                return;
            }

            console.log('Updating Cytoscape with', agents.value.length, 'agents,', connections.value.length, 'connections');
            console.log('Connection details:', connections.value.map(c => `${c.from}->${c.to} [${c.keyword}] (${c.type})`));

            // 如果是 keyword 更新（连接数不变），只更新边的 label 而不重新布局
            if (isKeywordUpdate) {
                console.log('[updateCytoscape] Keyword update - updating edge labels only');
                cytoscapeInstance.batch(() => {
                    connections.value.forEach(conn => {
                        // 查找对应的边并更新 keyword
                        const edges = cytoscapeInstance.edges().filter(e => {
                            return e.data('source') === conn.from &&
                                   e.data('target') === conn.to &&
                                   e.data('connType') === (conn.type || 'output');
                        });
                        edges.forEach(edge => {
                            edge.data('keyword', conn.keyword);
                        });
                    });
                });
                console.log('[updateCytoscape] Edge labels updated, layout preserved');
                return;
            }

            // 构建节点和边
            const elements = [];

            // 添加节点
            agents.value.forEach(agent => {
                // 计算连接数，用于动态调整节点大小
                const connectionCount = (agent.input_connections?.length || 0) +
                                       (agent.output_connections?.length || 0);
                const size = Math.min(100, Math.max(50, 50 + connectionCount * 5));
                // 截断ID用于显示
                const shortId = agent.id.substring(0, 8) + '...';

                elements.push({
                    data: {
                        id: agent.id,
                        label: shortId,
                        type: agent.type,
                        connectionCount: connectionCount
                    },
                    style: {
                        'width': size,
                        'height': size
                    }
                });
            });

            // 添加边
            connections.value.forEach(conn => {
                // 确保有 type 字段，默认为 output（兼容旧数据）
                const connType = conn.type || 'output';
                elements.push({
                    data: {
                        source: conn.from,
                        target: conn.to,
                        keyword: conn.keyword,
                        connType: connType
                    },
                    classes: connType === 'input' ? 'input-edge' : 'output-edge'
                });
            });

            console.log('Adding elements:', elements.length);

            // 更新数据 - 完全重建图以反映最新状态
            cytoscapeInstance.batch(() => {
                // 保留现有布局位置（如果存在）
                const nodePositions = {};
                cytoscapeInstance.nodes().forEach(node => {
                    nodePositions[node.id()] = {
                        x: node.position('x'),
                        y: node.position('y')
                    };
                });

                cytoscapeInstance.elements().remove();
                cytoscapeInstance.add(elements);

                // 恢复节点位置（避免布局跳动）
                Object.keys(nodePositions).forEach(nodeId => {
                    const node = cytoscapeInstance.getElementById(nodeId);
                    if (node) {
                        node.position(nodePositions[nodeId]);
                    }
                });
            });

            console.log('Elements updated, current edges:', cytoscapeInstance.edges().map(e => `${e.data('source')}->${e.data('target')}: ${e.data('keyword')}`));

            // 重新布局 - 使用力导向布局
            try {
                const layout = cytoscapeInstance.layout({
                    name: 'cose',
                    fit: true,
                    padding: 50,
                    animate: true,
                    animationDuration: 500,
                    // 力导向参数 - 调整以分散节点
                    componentSpacing: 200,
                    nodeRepulsion: 800000,
                    edgeElasticity: 50,
                    nestingFactor: 10,
                    gravity: 40,
                    numIter: 2000,
                    initialTemp: 400,
                    coolingFactor: 0.92,
                    minTemp: 1.0,
                    // 避免重叠
                    nodeOverlap: 40,
                    idealEdgeLength: 150
                });
                layout.run();
                console.log('Force-directed layout applied');
            } catch (e) {
                console.error('Layout error:', e);
                // 回退到网格布局
                const fallbackLayout = cytoscapeInstance.layout({
                    name: 'grid',
                    fit: true,
                    padding: 30
                });
                fallbackLayout.run();
            }
        }

        // 选择 Agent
        function selectAgent(agent) {
            selectedAgent.value = agent;
            // 请求详细信息
            if (ws && ws.readyState === WebSocket.OPEN) {
                ws.send(JSON.stringify({
                    type: 'get_agent',
                    agent_id: agent.id
                }));
            }
        }

        // 通过 ID 选择 Agent
        function selectAgentById(agentId) {
            const agent = agents.value.find(a => a.id === agentId);
            if (agent) {
                selectAgent(agent);
            }
        }

        // 格式化时间
        function formatTime(timestampUs) {
            if (!timestampUs) return '';
            const ms = timestampUs / 1000;
            const date = new Date(ms);
            return date.toLocaleTimeString('zh-CN', {
                hour12: false,
                hour: '2-digit',
                minute: '2-digit',
                second: '2-digit',
                fractionalSecondDigits: 3
            });
        }

        // 截断 ID
        function truncateId(id) {
            if (!id) return '';
            if (id.length <= 12) return id;
            return id.substring(0, 8) + '...' + id.substring(id.length - 4);
        }

        // 格式化日志数据
        function formatLogData(data) {
            if (!data) return '';
            return Object.entries(data)
                .map(([k, v]) => `${k}: ${JSON.stringify(v).substring(0, 50)}`)
                .join(', ');
        }

        // 过滤日志
        const filteredLogs = computed(() => {
            if (!logFilter.value) return logs.value;
            const filter = logFilter.value.toLowerCase();
            return logs.value.filter(log =>
                log.source?.toLowerCase().includes(filter) ||
                log.event_type?.toLowerCase().includes(filter) ||
                JSON.stringify(log.data).toLowerCase().includes(filter)
            );
        });

        // 生命周期
        onMounted(() => {
            connectWebSocket();
            // 等待 DOM 渲染后初始化 Cytoscape
            setTimeout(initCytoscape, 100);
        });

        return {
            isConnected,
            logs,
            logFilter,
            agents,
            connections,
            selectedAgent,
            logContainer,
            asyncState,
            recentFlows,
            filteredLogs,
            selectAgent,
            formatTime,
            truncateId,
            formatLogData,
            handleMessageFlow,
            handleAgentActivated,
            fitTopology,
            resetLayout,
            toggleLayout
        };
    }
}).mount('#app');
