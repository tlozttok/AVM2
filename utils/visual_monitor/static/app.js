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

        // WebSocket 连接
        let ws = null;
        let cytoscapeInstance = null;

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
                const data = JSON.parse(event.data);
                handleMessage(data);
            };
        }

        // 处理 WebSocket 消息
        function handleMessage(data) {
            const type = data.type;

            if (type === 'init') {
                // 初始数据
                if (data.topology) {
                    agents.value = data.topology.agents || [];
                    connections.value = data.topology.connections || [];
                    updateCytoscape();
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
                if (data.topology) {
                    agents.value = data.topology.agents || [];
                    connections.value = data.topology.connections || [];
                    updateCytoscape();
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
                // 找到对应的边并高亮
                const edge = cytoscapeInstance.edges().filter(e =>
                    e.data('source') === from && e.data('target') === to
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
                            'line-color': '#60a5fa',
                            'target-arrow-color': '#60a5fa',
                            'width': 2
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
                    // 高亮节点
                    node.animate({
                        style: {
                            'background-color': '#4ade80',
                            'border-width': 3,
                            'border-color': '#fff'
                        }
                    }, {
                        duration: 300
                    }).animate({
                        style: {
                            'background-color': '#e94560',
                            'border-width': 0
                        }
                    }, {
                        duration: 500
                    });
                }
            }
        }

        // Cytoscape 拓扑图
        function initCytoscape() {
            cytoscapeInstance = cytoscape({
                container: document.getElementById('cytoplasm'),
                style: [
                    {
                        selector: 'node',
                        style: {
                            'background-color': '#e94560',
                            'label': 'data(id)',
                            'text-valign': 'center',
                            'text-halign': 'center',
                            'text-fill-color': '#fff',
                            'text-outline-color': '#000',
                            'text-outline-width': 1,
                            'width': 60,
                            'height': 60,
                            'font-size': '10px'
                        }
                    },
                    {
                        selector: 'edge',
                        style: {
                            'width': 2,
                            'line-color': '#60a5fa',
                            'target-arrow-color': '#60a5fa',
                            'target-arrow-shape': 'triangle',
                            'curve-style': 'bezier',
                            'label': 'data(keyword)',
                            'font-size': '8px',
                            'text-rotation': 'autorotate',
                            'text-margin-y': -10
                        }
                    },
                    {
                        selector: 'node:selected',
                        style: {
                            'background-color': '#f472b6',
                            'border-width': 3,
                            'border-color': '#fff'
                        }
                    }
                ],
                layout: {
                    name: 'cose',
                    animate: true,
                    animationDuration: 500,
                    nodeOverlap: 20,
                    idealEdgeLength: 100,
                    edgeElasticity: 100
                }
            });

            // 点击节点事件
            cytoscapeInstance.on('tap', 'node', (event) => {
                const node = event.target;
                const agentId = node.data('id');
                selectAgentById(agentId);
            });
        }

        // 更新拓扑图
        function updateCytoscape() {
            if (!cytoscapeInstance) {
                initCytoscape();
            }

            // 构建节点和边
            const elements = [];

            // 添加节点
            agents.value.forEach(agent => {
                elements.push({
                    data: {
                        id: agent.id,
                        type: agent.type
                    }
                });
            });

            // 添加边
            connections.value.forEach(conn => {
                elements.push({
                    data: {
                        source: conn.from,
                        target: conn.to,
                        keyword: conn.keyword
                    }
                });
            });

            // 更新数据
            cytoscapeInstance.elements().remove();
            cytoscapeInstance.add(elements);

            // 重新布局
            const layout = cytoscapeInstance.layout({
                name: 'cose',
                animate: true,
                animationDuration: 300
            });
            layout.run();
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
            handleAgentActivated
        };
    }
}).mount('#app');
