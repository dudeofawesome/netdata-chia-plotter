from random import SystemRandom
from bases.FrameworkServices.SimpleService import SimpleService
import os
import subprocess
import glob

# try:
#   import plotman
#   HAS_PLOTMAN = True
# except ImportError:
#   HAS_PLOTMAN = False

NETDATA_UPDATE_EVERY = 15
priority = 90000

ORDER = [
    'in_prog_plots', 'farmable_plots', 'phase', 'state', 'wall'
]

CHARTS = {
    'in_prog_plots': {
        #           name  title                units    family   context  chart type
        'options': [None, 'Plots in progress', 'plots', 'plots', 'plots', 'area'],
        'lines': [
          # unique_dimension_name, name, algorithm, multiplier, divisor
          ['in_prog_plots', 'in progress'],
          ['paused_plots', 'paused'],
        ]
    },
    'farmable_plots': {
        #           name  title                units    family   context  chart type
        'options': [None, 'Farmable plots', 'plots', 'plots', 'plots', 'area'],
        #          unique_dimension_name, name, algorithm, multiplier, divisor
        'lines': [['farmable_plots', 'farmable']]
    },
    'phase': {
        #           name  title                         units               family   context  chart type
        'options': [None, 'The phase of the chia plot', 'chia plots phase', 'phase', 'phase', 'line'],
        'lines': []
    },
    'state': {
        #           name  title                         units              family   context  chart type
        'options': [None, 'The state of the chia plot', 'chia plot state', 'state', 'state', 'line'],
        'lines': []
    },
    'wall': {
        #           name  title        units    family  context chart type
        'options': [None, 'Who knows', 'hours', 'wall', 'wall', 'line'],
        'lines': []
    },
}


class Service(SimpleService):
  def __init__(self, configuration=None, name=None):
    SimpleService.__init__(self, configuration=configuration, name=name)
    self.order = ORDER
    self.definitions = CHARTS
    self.plot_path_globs = configuration.get('plot_path_globs', ['/mnt/*'])
    self.debug(self.plot_path_globs)

  def check(self):
    return True
    # if not HAS_PLOTMAN:
    #   self.error("'plotman' package is needed to use chia_plotter module")
    #   return False

  def get_data(self):
    data = dict()

    plots = read_plotman()
    self.debug(len(plots), 'plots in progress')

    if 'in_prog_plots' not in self.charts['in_prog_plots']:
      self.charts['in_prog_plots'].add_dimension(['in_prog_plots'])
    data['in_prog_plots'] = len(list(filter(lambda plot: plot.state != 'STP', plots)))

    if 'paused_plots' not in self.charts['in_prog_plots']:
      self.charts['in_prog_plots'].add_dimension(['paused_plots'])
    data['paused_plots'] = -len(list(filter(lambda plot: plot.state == 'STP', plots)))

    if 'farmable_plots' not in self.charts['farmable_plots']:
      self.charts['farmable_plots'].add_dimension(['farmable_plots'])
    
    farmable_plots = get_farmable_plots(self.plot_path_globs)
    self.debug(farmable_plots)
    data['farmable_plots'] = len(farmable_plots)

    for i in range(0, len(plots)):
      base_dimension_id = ''.join([plots[i].cache, ':', plots[i].id])
      phase_id = ''.join(['phase_', base_dimension_id])
      state_id = ''.join(['state_', base_dimension_id])
      wall_id = ''.join(['wall_', base_dimension_id])

      if phase_id not in self.charts['phase']:
        self.charts['phase'].add_dimension([phase_id, None, None, None, 10])
      if state_id not in self.charts['state']:
        self.charts['state'].add_dimension([state_id])
      if wall_id not in self.charts['wall']:
        self.charts['wall'].add_dimension([wall_id])

      phase = plots[i].phase.split(':')
      data[phase_id] = (float(phase[0]) + (float(phase[1]) / 10)) * 10.0
      self.debug(data[phase_id])

      # data[state_id] = plots[i].state

      # data[wall_id] = plots[i].wall

    return data

def read_plotman():
  lines = subprocess.run(
      ['cat', '/var/tmp/plotman-status.out'],
      # ['plotman', 'status'],
      # cwd='/usr/local/src/chia-blockchain',
      # # env=dict(PATH=''.join([os.getenv('PATH'),':/usr/bin:/bin:/usr/sbin:/sbin:/home/dudeofawesome/chia-blockchain/activate/bin'])),
      # env=dict(
      #   PATH=''.join([os.getenv('PATH'),':/usr/local/src/chia-blockchain/activate/bin']),
      #   VIRTUAL_ENV='/usr/local/src/chia-blockchain/activate',
      # ),
      capture_output=True,
      text=True,
    ).stdout.split('\n')
  lines = list(filter(lambda line: line != None and len(line) != 0, lines))
  lines = list(filter(lambda line: not line.strip().startswith('plot'), lines))

  for i in range(len(lines)):
    split = lines[i].split()
    if len(split) < 13:
      raise Exception(''.join(['Invalid input ', lines[i]]))

    lines[i] = Plot(
      id=split[0],
      k=split[1],
      cache=split[2],
      dest=split[3],
      wall=split[4],
      phase=split[5],
      cache_size=split[6],
      pid=split[7],
      state=split[8],
      memory=split[9],
      user=split[10],
      sys=split[11],
      io=split[12],
    )
  
  return lines

def get_farmable_plots(plot_path_globs):
  plots = []

  for plot_path_glob in plot_path_globs:
    for cache_dir in glob.glob(plot_path_glob):
      for plot in glob.glob(''.join([cache_dir, '/plots/*k32*.plot'])):
        plots.append(plot)  

  return plots

class Plot():
  def __init__(
    self, id=None, k=None, cache=None, dest=None, wall=None, phase=None,
    cache_size=None, pid=None, state=None, memory=None, user=None, sys=None,
    io=None
  ):
    self.id = id
    self.k = k
    self.cache = cache
    self.dest = dest
    self.wall = wall
    self.phase = phase
    self.cache_size = cache_size
    self.pid = pid
    self.state = state
    self.memory = memory
    self.user = user
    self.sys = sys
    self.io = io
