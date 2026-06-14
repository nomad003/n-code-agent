class SceneMgr:
    """场景管理器：负责加载、切换和卸载游戏场景。"""

    def __init__(self):
        self.current_scene = None
        self.scenes = {}

    def load_scene(self, scene_id):
        """加载指定 id 的场景。"""
        self.current_scene = scene_id
