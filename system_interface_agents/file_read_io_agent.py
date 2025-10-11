import json
import os
from driver.system_agents import IOAgent

class FileReadIOAgent(IOAgent):
    
    
    
    
    
    def _process_query(self, query_content):
        query_sender_keyword = query_content.sender_keyword
        query_receiver_keyword = query_content.receiver_keyword
        content=query_content.content
        
        content=json.loads(content)
        file_path=content["file_path"]
        start_point=content.get("start_point",0)
        length=content.get("length",200)
        
        response=""
        
        if not isinstance(file_path, str):
            self.logger.warning("file_path参数必须是字符串")
            response+="错误：file_path参数必须是字符串 "
        if not isinstance(start_point, int):
            self.logger.warning("start_point参数必须是整数")
            response+="错误：start_point参数必须是整数 "
        if not isinstance(length, int):
            self.logger.warning("length参数必须是整数")
            response+="错误：length参数必须是整数 "
        if start_point<0:
            self.logger.warning("start_point参数必须大于等于0")
            response+="错误：start_point参数必须大于等于0 "
        if length<=0:
            self.logger.warning("length参数必须大于0")
            response+="错误：length参数必须大于0 "
            
        if not os.path.exists(file_path):
            self.logger.warning(f"文件不存在: {file_path}")
            response+="错误：文件不存在 "
        else:
            file_size = os.path.getsize(file_path)
            if start_point>=file_size:
                self.logger.warning(f"start_point参数超出文件大小: {file_path}")
                response+="错误：start_point参数超出文件大小 "

        
        
        if "错误" in response:
            return f"<{query_receiver_keyword}>"+response+f"</{query_receiver_keyword}>"
        
        # 有些不对劲
        # IOAgent的设计也许存在本质的问题
        # 自我同一系统不应该存在即时局部指令查询
        # 而IOAgent的设计使得要不然就选择局部查询，要不然就只能广播
        # 一个Agent想要消息，结果产生广播，这不好
        # 所以还是选择一个InputAgent加一个OutputAgent来处理
        # 这也导致Agent内部信息分散，促进Agent之间的形成连接，将信息从InputAgent计算并传递到OutputAgent
        
        with open(file_path, 'r', encoding='utf-8') as f:
            f.seek(start_point)
            file_content = f.read(length)
            response+=file_content
            
        return f"<{query_receiver_keyword}>"+response+f"</{query_receiver_keyword}>"
        
