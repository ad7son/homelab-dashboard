"""將五種實際採集器組合成應用層需要的 MetricsSource。"""
class SystemMetricsSource:
    def __init__(self, cpu, memory, network, gpu, disk_io):
        self.cpu_reader, self.memory_reader = cpu, memory
        self.network_reader, self.gpu_reader, self.disk_io_reader = network, gpu, disk_io

    def cpu(self):
        return self.cpu_reader.read()

    def memory(self):
        return self.memory_reader.read()

    def network(self):
        return self.network_reader.read()

    def gpu(self):
        return self.gpu_reader.read()

    def disk_io(self):
        return self.disk_io_reader.read()
