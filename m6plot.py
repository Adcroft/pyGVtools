"""
A method for producing a standardized pseudo-colot plot of 2D data
"""

import numpy, numpy.matlib
import matplotlib.pyplot as plt
from matplotlib.colors import BoundaryNorm, ListedColormap
from matplotlib.ticker import MaxNLocator
import math
import m6toolbox


def xyplot(field, x=None, y=None, area=None,
  xLabel=None, xUnits=None, yLabel=None, yUnits=None,
  title='', suptitle='', nBins=None, cLim=None, landColor=[.5,.5,.5], colormap=None, extend=None,
  aspect=[16,9], resolution=576,
  ignore=None, save=None, debug=False, show=False, interactive=False):
  """
  Renders plot of scalar field, field(x,y).

  Arguments:
  field       Scalar 2D array to be plotted.
  x           x coordinate (1D or 2D array). If x is the same size as field then x is treated as
              the cell center coordinates.
  y           y coordinate (1D or 2D array). If x is the same size as field then y is treated as
              the cell center coordinates.
  area        2D array of cell areas (used for statistics). Default None.
  xLabel      The label for the x axis. Default 'Longitude'.
  xUnits      The units for the x axis. Default 'degrees E'.
  yLabel      The label for the y axis. Default 'Latitude'.
  yUnits      The units for the y axis. Default 'degrees N'.
  title       The title to place at the top of the panel. Default ''.
  suptitle    The super-title to place at the top of the figure. Default ''.
  nBins       The number of colors levels (used is cLim is missing or only specifies the color range).
  cLim        A tuple of (min,max) color range OR a list of contour levels. Default None.
  landColor   An rgb tuple to use for the color of land (no data). Default [.5,.5,.5].
  colormap    The name of the colormap to use. Default None.
  extend      Can be one of 'both', 'neither', 'max', 'min'. Default None.
  aspect      The aspect ratio of the figure, given as a tuple (W,H). Default [16,9].
  resolution  The vertical rseolutin of the figure given in pixels. Default 720.
  ignore      A value to use as no-data (NaN). Default None.
  save        Name of file to save figure in. Default None.
  debug       If true, report sutff for debugging. Default False.
  show        If true, causes the figure to appear on screen. Used for testing. Default False.
  interactive If true, adds interactive features such as zoom, close and cursor. Default False.
  """

  # Create coordinates if not provided
  xLabel, xUnits, yLabel, yUnits = createXYlabels(x, y, xLabel, xUnits, yLabel, yUnits)
  if debug: print 'x,y label/units=',xLabel,xUnits,yLabel,yUnits
  xCoord, yCoord = createXYcoords(field, x, y)

  # Diagnose statistics
  if ignore!=None: maskedField = numpy.ma.masked_array(field, mask=[field==ignore])
  else: maskedField = field.copy()
  sMin, sMax, sMean, sStd, sRMS = myStats(maskedField, area, debug=debug)
  xLims = boundaryStats(xCoord)
  yLims = boundaryStats(yCoord)

  # Choose colormap
  if nBins==None and (cLim==None or len(cLim)==2): nBins=35
  if colormap==None: colormap = chooseColorMap(sMin, sMax)
  cmap, norm, extend = chooseColorLevels(sMin, sMax, colormap, cLim=cLim, nBins=nBins, extend=extend)

  setFigureSize(aspect, resolution, debug=debug)
  #plt.gcf().subplots_adjust(left=.08, right=.99, wspace=0, bottom=.09, top=.9, hspace=0)
  axis = plt.gca()
  plt.pcolormesh(xCoord, yCoord, maskedField, cmap=cmap, norm=norm)
  if interactive: addStatusBar(xCoord, yCoord, maskedField)
  plt.colorbar(fraction=.08, pad=0.02, extend=extend)
  plt.gca().set_axis_bgcolor(landColor)
  plt.xlim( xLims )
  plt.ylim( yLims )
  axis.annotate('max=%.5g\nmin=%.5g'%(sMax,sMin), xy=(0.0,1.01), xycoords='axes fraction', verticalalignment='bottom', fontsize=10)
  if area!=None:
    axis.annotate('mean=%.5g\nrms=%.5g'%(sMean,sRMS), xy=(1.0,1.01), xycoords='axes fraction', verticalalignment='bottom', horizontalalignment='right', fontsize=10)
    axis.annotate(' sd=%.5g\n'%(sStd), xy=(1.0,1.01), xycoords='axes fraction', verticalalignment='bottom', horizontalalignment='left', fontsize=10)
  if len(xLabel+xUnits)>0: plt.xlabel(label(xLabel, xUnits))
  if len(yLabel+yUnits)>0: plt.ylabel(label(yLabel, yUnits))
  if len(title)>0: plt.title(title)
  if len(suptitle)>0: plt.suptitle(suptitle)

  if save!=None: plt.savefig(save)
  if interactive: addInteractiveCallbacks()
  if show: plt.show(block=False)


def addInteractiveCallbacks():
  """
  Adds interactive features to a plot on screen.
  Key 'q' to close window.
  Zoom button to center.
  Zoom wheel to zoom in and out.
  """
  def keyPress(event):
    if event.key=='Q': exit(0) # Exit python
    elif event.key=='q': plt.close() # Close just the active figure
  class hiddenStore:
    def __init__(self,axis):
      self.axis = axis
      self.xMin, self.xMax = axis.get_xlim()
      self.yMin, self.yMax = axis.get_ylim()
  save = hiddenStore(plt.gca())
  def zoom(event): # Scroll wheel up/down
    if event.button == 'up': scaleFactor = 1/1.5 # deal with zoom in
    elif event.button == 'down': scaleFactor = 1.5 # deal with zoom out
    elif event.button == 2: scaleFactor = 1.0
    else: return
    axis = event.inaxes
    axmin,axmax=axis.get_xlim(); aymin,aymax=axis.get_ylim();
    (axmin,axmax),(aymin,aymax) = newLims(
        (axmin,axmax), (aymin,aymax), (event.xdata, event.ydata),
        (save.xMin,save.xMax), (save.yMin,save.yMax), scaleFactor)
    if axmin==None: return
    for axis in plt.gcf().get_axes():
      if axis.get_navigate():
        axis.set_xlim(axmin, axmax); axis.set_ylim(aymin, aymax)
    plt.draw() # force re-draw
  def zoom2(event): zoom(event)
  plt.gcf().canvas.mpl_connect('key_press_event', keyPress)
  plt.gcf().canvas.mpl_connect('scroll_event', zoom)
  plt.gcf().canvas.mpl_connect('button_press_event', zoom2)


def addStatusBar(xCoord, yCoord, zData):
  """
  Reformats status bar message
  """
  class hiddenStore:
    def __init__(self,axis):
      self.axis = axis
      self.xMin, self.xMax = axis.get_xlim()
      self.yMin, self.yMax = axis.get_ylim()
  save = hiddenStore(plt.gca())
  def statusMessage(x,y):
    # THIS NEEDS TESTING FOR ACCURACY, ESPECIALLY IN YZ PLOTS -AJA
    if len(xCoord.shape)==1 and len(yCoord.shape)==1:
      # -2 needed because of coords are for vertices and need to be averaged to centers
      i = min(range(len(xCoord)-2), key=lambda l: abs((xCoord[l]+xCoord[l+1])/2.-x))
      j = min(range(len(yCoord)-2), key=lambda l: abs((yCoord[l]+yCoord[l+1])/2.-y))
    elif len(xCoord.shape)==1 and len(yCoord.shape)==2:
      i = min(range(len(xCoord)-2), key=lambda l: abs((xCoord[l]+xCoord[l+1])/2.-x))
      j = min(range(len(yCoord[:,i])-1), key=lambda l: abs((yCoord[l,i]+yCoord[l+1,i])/2.-y))
    elif len(xCoord.shape)==2 and len(yCoord.shape)==2:
      idx = numpy.abs( numpy.fabs( xCoord[0:-1,0:-1]+xCoord[1:,1:]+xCoord[0:-1,1:]+xCoord[1:,0:-1]-4*x)
          +numpy.fabs( yCoord[0:-1,0:-1]+yCoord[1:,1:]+yCoord[0:-1,1:]+yCoord[1:,0:-1]-4*y) ).argmin()
      j,i = numpy.unravel_index(idx,zData.shape)
    else: raise Exception('Combindation of coordinates shapes is VERY UNUSUAL!')
    if not i==None:
      val = zData[j,i]
      if val is numpy.ma.masked: return 'x,y=%.3f,%.3f  f(%i,%i)=NaN'%(x,y,i+1,j+1)
      else: return 'x,y=%.3f,%.3f  f(%i,%i)=%g'%(x,y,i+1,j+1,val)
    else: return 'x,y=%.3f,%.3f'%(x,y)
  plt.gca().format_coord = statusMessage


def newLims(cur_xlim, cur_ylim, cursor, xlim, ylim, scale_factor):
  cur_xrange = (cur_xlim[1] - cur_xlim[0])*.5
  cur_yrange = (cur_ylim[1] - cur_ylim[0])*.5
  xdata = cursor[0]; ydata = cursor[1]
  new_xrange = cur_xrange*scale_factor; new_yrange = cur_yrange*scale_factor
  xdata = min( max( xdata, xlim[0]+new_xrange ), xlim[1]-new_xrange )
  xL = max( xlim[0], xdata - new_xrange ); xR = min( xlim[1], xdata + new_xrange )
  if ylim[1]>ylim[0]:
    ydata = min( max( ydata, ylim[0]+new_yrange ), ylim[1]-new_yrange )
    yL = max( ylim[0], ydata - new_yrange ); yR = min( ylim[1], ydata + new_yrange )
  else:
    ydata = min( max( ydata, ylim[1]-new_yrange ), ylim[0]+new_yrange )
    yR = max( ylim[1], ydata + new_yrange ); yL = min( ylim[0], ydata - new_yrange )
  if xL==cur_xlim[0] and xR==cur_xlim[1] and \
     yL==cur_ylim[0] and yR==cur_ylim[1]: return (None, None), (None, None)
  return (xL, xR), (yL, yR)


def xycompare(field1, field2, x=None, y=None, area=None,
  xLabel=None, xUnits=None, yLabel=None, yUnits=None,
  title1='', title2='', title3='A - B', addPlabel=True, suptitle='',
  nBins=None, cLim=None, dLim=None, landColor=[.5,.5,.5], colormap=None, dcolormap=None, extend=None,
  aspect=None, resolution=None, nPanels=3,
  ignore=None, save=None, debug=False, show=False, interactive=False):
  """
  Renders n-panel plot of two scalar fields, field1(x,y) and field2(x,y).

  Arguments:
  field1      Scalar 2D array to be plotted and compared to field2.
  field2      Scalar 2D array to be plotted and compared to field1.
  x           x coordinate (1D or 2D array). If x is the same size as field then x is treated as
              the cell center coordinates.
  y           y coordinate (1D or 2D array). If x is the same size as field then y is treated as
              the cell center coordinates.
  area        2D array of cell areas (used for statistics). Default None.
  xLabel      The label for the x axis. Default 'Longitude'.
  xUnits      The units for the x axis. Default 'degrees E'.
  yLabel      The label for the y axis. Default 'Latitude'.
  yUnits      The units for the y axis. Default 'degrees N'.
  title1      The title to place at the top of panel 1. Default ''.
  title2      The title to place at the top of panel 1. Default ''.
  title3      The title to place at the top of panel 1. Default 'A-B'.
  addPlabel   Adds a 'A:' or 'B:' to the title1 and title2. Default True.
  suptitle    The super-title to place at the top of the figure. Default ''.
  nBins       The number of colors levels (used is cLim is missing or only specifies the color range).
  cLim        A tuple of (min,max) color range OR a list of contour levels for the field plots. Default None.
  dLim        A tuple of (min,max) color range OR a list of contour levels for the difference plot. Default None.
  landColor   An rgb tuple to use for the color of land (no data). Default [.5,.5,.5].
  colormap    The name of the colormap to use for the field plots. Default None.
  dcolormap   The name of the colormap to use for the differece plot. Default None.
  extend      Can be one of 'both', 'neither', 'max', 'min'. Default None.
  aspect      The aspect ratio of the figure, given as a tuple (W,H). Default [16,9].
  resolution  The vertical rseolutin of the figure given in pixels. Default 1280.
  nPanels     Number of panels to display (1, 2 or 3). Default 3.
  ignore      A value to use as no-data (NaN). Default None.
  save        Name of file to save figure in. Default None.
  debug       If true, report sutff for debugging. Default False.
  show        If true, causes the figure to appear on screen. Used for testing. Default False.
  interactive If true, adds interactive features such as zoom, close and cursor. Default False.
  """

  if (field1.shape)!=(field2.shape): raise Exception('field1 and field2 must be the same shape')

  # Create coordinates if not provided
  xLabel, xUnits, yLabel, yUnits = createXYlabels(x, y, xLabel, xUnits, yLabel, yUnits)
  if debug: print 'x,y label/units=',xLabel,xUnits,yLabel,yUnits
  xCoord, yCoord = createXYcoords(field1, x, y)

  # Diagnose statistics
  if ignore!=None: maskedField1 = numpy.ma.masked_array(field1, mask=[field1==ignore])
  else: maskedField1 = field1.copy()
  s1Min, s1Max, s1Mean, s1Std, s1RMS = myStats(maskedField1, area, debug=debug)
  if ignore!=None: maskedField2 = numpy.ma.masked_array(field2, mask=[field2==ignore])
  else: maskedField2 = field2.copy()
  s2Min, s2Max, s2Mean, s2Std, s2RMS = myStats(maskedField2, area, debug=debug)
  dMin, dMax, dMean, dStd, dRMS = myStats(maskedField1 - maskedField2, area, debug=debug)
  if s1Mean!=None: dRxy = corr(maskedField1 - s1Mean, maskedField2 - s2Mean, area)
  else: dRxy = None
  s12Min = min(s1Min, s2Min); s12Max = max(s1Max, s2Max)
  xLims = boundaryStats(xCoord); yLims = boundaryStats(yCoord)
  if debug:
    print 's1: min, max, mean =', s1Min, s1Max, s1Mean
    print 's2: min, max, mean =', s2Min, s2Max, s2Mean
    print 's12: min, max =', s12Min, s12Max

  # Choose colormap
  if nBins==None and (cLim==None or len(cLim)==2): cBins=35
  else: cBins=nBins
  if nBins==None and (dLim==None or len(dLim)==2): nBins=35
  if colormap==None: colormap = chooseColorMap(s12Min, s12Max)
  cmap, norm, extend = chooseColorLevels(s12Min, s12Max, colormap, cLim=cLim, nBins=cBins, extend=extend)

  def annotateStats(axis, sMin, sMax, sMean, sStd, sRMS):
    axis.annotate('max=%.5g\nmin=%.5g'%(sMax,sMin), xy=(0.0,1.025), xycoords='axes fraction', verticalalignment='bottom', fontsize=10)
    if sMean!=None:
      axis.annotate('mean=%.5g\nrms=%.5g'%(sMean,sRMS), xy=(1.0,1.025), xycoords='axes fraction', verticalalignment='bottom', horizontalalignment='right', fontsize=10)
      axis.annotate(' sd=%.5g\n'%(sStd), xy=(1.0,1.025), xycoords='axes fraction', verticalalignment='bottom', horizontalalignment='left', fontsize=10)

  if addPlabel: preTitleA = 'A: '; preTitleB = 'B: '
  else: preTitleA = ''; preTitleB = ''

  setFigureSize(aspect, resolution, nPanels, debug=debug)

  if nPanels in [2,3]:
    plt.subplot(nPanels,1,1)
    plt.pcolormesh(xCoord, yCoord, maskedField1, cmap=cmap, norm=norm)
    if interactive: addStatusBar(xCoord, yCoord, maskedField1)
    plt.colorbar(fraction=.08, pad=0.02, extend=extend)
    plt.gca().set_axis_bgcolor(landColor)
    plt.xlim( xLims ); plt.ylim( yLims )
    annotateStats(plt.gca(), s1Min, s1Max, s1Mean, s1Std, s1RMS)
    plt.gca().set_xticklabels([''])
    if len(yLabel+yUnits)>0: plt.ylabel(label(yLabel, yUnits))
    if len(title1)>0: plt.title(preTitleA+title1)

    plt.subplot(nPanels,1,2)
    plt.pcolormesh(xCoord, yCoord, maskedField2, cmap=cmap, norm=norm)
    if interactive: addStatusBar(xCoord, yCoord, maskedField2)
    plt.colorbar(fraction=.08, pad=0.02, extend=extend)
    plt.gca().set_axis_bgcolor(landColor)
    plt.xlim( xLims ); plt.ylim( yLims )
    annotateStats(plt.gca(), s2Min, s2Max, s2Mean, s2Std, s2RMS)
    if nPanels>2: plt.gca().set_xticklabels([''])
    if len(yLabel+yUnits)>0: plt.ylabel(label(yLabel, yUnits))
    if len(title2)>0: plt.title(preTitleB+title2)

  if nPanels in [1,3]:
    plt.subplot(nPanels,1,nPanels)
    if dcolormap==None: dcolormap = chooseColorMap(dMin, dMax)
    cmap, norm, extend = chooseColorLevels(dMin, dMax, dcolormap, cLim=dLim, nBins=nBins, extend=extend)
    plt.pcolormesh(xCoord, yCoord, maskedField1 - maskedField2, cmap=cmap, norm=norm)
    if interactive: addStatusBar(xCoord, yCoord, maskedField1 - maskedField2)
    plt.colorbar(fraction=.08, pad=0.02, extend=extend)
    plt.gca().set_axis_bgcolor(landColor)
    plt.xlim( xLims ); plt.ylim( yLims )
    annotateStats(plt.gca(), dMin, dMax, dMean, dStd, dRMS)
    if len(yLabel+yUnits)>0: plt.ylabel(label(yLabel, yUnits))
    if len(title3)>0: plt.title(title3)

  if dRxy!=None: plt.gca().annotate(' r(A,B)=%.5g\n'%(dRxy), xy=(1.0,-0.20), xycoords='axes fraction', verticalalignment='bottom', horizontalalignment='center', fontsize=10)
  if len(xLabel+xUnits)>0: plt.xlabel(label(xLabel, xUnits))
  if len(suptitle)>0: plt.suptitle(suptitle)

  if save!=None: plt.savefig(save)
  if interactive: addInteractiveCallbacks()
  if show: plt.show(block=False)


def chooseColorMap(sMin, sMax):
  """
  Based on the min/max extremes of the data, choose a colormap that fits the data.
  """
  if sMin<0 and sMax>0: return 'seismic'
  elif sMax>0 and sMin<0.1*sMax: return 'hot'
  elif sMin<0 and sMax>0.1*sMin: return 'hot_r'
  else: return 'spectral'


def chooseColorLevels(sMin, sMax, colorMapName, cLim=None, nBins=None, steps=[1,2,2.5,5,10], extend=None):
  """
  If nBins is a positive integer, choose sensible color levels with nBins colors.
  If cLim is a 2-element tuple, create color levels within the cLim range
  or if cLim is a vector, use cLim as contour levels.
  If cLim provides more than 2 color interfaces, nBins must be absent.
  If cLim is absent, the sMin,sMax are used as the color range bounds.
  
  Returns cmap, norm and extend.
  """
  if nBins==None and cLim==None: raise Exception('At least one of cLim or nBins is required.')
  if cLim!=None:
    if len(cLim)<2: raise Exception('cLim must be at least 2 values long.')
    if nBins==None and len(cLim)==2: raise Exception('nBins must be provided when cLims specifies a color range.')
    if nBins!=None and len(cLim)>2: raise Exception('nBins cannot be provided when cLims specifies color levels.')
  if cLim==None: levels = MaxNLocator(nbins=nBins, steps=steps).tick_values(sMin, sMax)
  elif len(cLim)==2: levels = MaxNLocator(nbins=nBins, steps=steps).tick_values(cLim[0], cLim[1])
  else: levels = cLim

  nColors = len(levels)-1
  if extend==None:
    if sMin<levels[0] and sMax>levels[-1]: extend = 'both'#; eColors=[1,1]
    elif sMin<levels[0] and sMax<=levels[-1]: extend = 'min'#; eColors=[1,0]
    elif sMin>=levels[0] and sMax>levels[-1]: extend = 'max'#; eColors=[0,1]
    else: extend = 'neither'#; eColors=[0,0]
  eColors = [0,0]
  if extend in ['both', 'min']: eColors[0] = 1
  if extend in ['both', 'max']: eColors[1] = 1

  cmap = plt.cm.get_cmap(colorMapName,lut=nColors+eColors[0]+eColors[1])
  cmap0 = cmap(0.)
  cmap1 = cmap(1.)
  cmap = ListedColormap(cmap(range(eColors[0],nColors+1-eColors[1]+eColors[0])))#, N=nColors)
  if eColors[0]>0: cmap.set_under(cmap0)
  if eColors[1]>0: cmap.set_over(cmap1)
  norm = BoundaryNorm(levels, ncolors=cmap.N)
  return cmap, norm, extend


def myStats(s, area, s2=None, debug=False):
  """
  Calculates mean, standard deviation and root-mean-square of s.
  """
  sMin = numpy.ma.min(s); sMax = numpy.ma.max(s)
  if area==None: return sMin, sMax, None, None, None
  weight = area.copy()
  if debug: print 'myStats: sum(area) =',numpy.ma.sum(weight)
  if not numpy.ma.getmask(s).any()==numpy.ma.nomask: weight[s.mask] = 0.
  sumArea = numpy.ma.sum(weight)
  if debug: print 'myStats: sum(area) =',sumArea,'after masking'
  if debug: print 'myStats: sum(s) =',numpy.ma.sum(s)
  if debug: print 'myStats: sum(area*s) =',numpy.ma.sum(weight*s)
  mean = numpy.ma.sum(weight*s)/sumArea
  std = math.sqrt( numpy.ma.sum( weight*((s-mean)**2) )/sumArea )
  rms = math.sqrt( numpy.ma.sum( weight*(s**2) )/sumArea )
  if debug: print 'myStats: mean(s) =',mean
  if debug: print 'myStats: std(s) =',std
  if debug: print 'myStats: rms(s) =',rms
  return sMin, sMax, mean, std, rms


def corr(s1, s2, area):
  """
  Calculates the correlation coefficient between s1 and s2, assuming s1 and s2 have
  not mean. That is s1 = S - mean(S), etc.
  """
  weight = area.copy()
  if not numpy.ma.getmask(s1).any()==numpy.ma.nomask: weight[s1.mask] = 0.
  sumArea = numpy.ma.sum(weight)
  v1 = numpy.ma.sum( weight*(s1**2) )/sumArea
  v2 = numpy.ma.sum( weight*(s2**2) )/sumArea
  if v1==0 or v2==0: return numpy.NaN
  rxy = numpy.ma.sum( weight*(s1*s2) )/sumArea / math.sqrt( v1*v2 )
  return rxy


def createXYcoords(s, x, y):
  """
  Checks that x and y are appropriate 2D corner coordinates
  and tries to make some if they are not.
  """
  nj, ni = s.shape
  if x==None: xCoord = numpy.arange(0., ni+1)
  else: xCoord = numpy.ma.filled(x, 0.)
  if y==None: yCoord = numpy.arange(0., nj+1)
  else: yCoord = numpy.ma.filled(y, 0.)

  # Turn coordinates into 2D arrays if 1D arrays were provided
  if len(xCoord.shape)==1:
    nxy = yCoord.shape
    xCoord = numpy.matlib.repmat(xCoord, nxy[0], 1)
  nxy = xCoord.shape
  if len(yCoord.shape)==1: yCoord = numpy.matlib.repmat(yCoord.T, nxy[-1], 1).T
  if xCoord.shape!=yCoord.shape: raise Exception('The shape of coordinates are mismatched!')

  # Create corner coordinates from center coordinates is center coordinates were provided
  if xCoord.shape!=yCoord.shape: raise Exception('The shape of coordinates are mismatched!')
  if s.shape==xCoord.shape:
    xCoord = expandJ( expandI( xCoord ) )
    yCoord = expandJ( expandI( yCoord ) )
  return xCoord, yCoord


def expandI(a):
  """
  Expands an array by one column, averaging the data to the middle columns and
  extrapolating for the first and last columns. Needed for shifting coordinates
  from centers to corners.
  """
  nj, ni = a.shape
  b = numpy.zeros((nj, ni+1))
  b[:,1:-1] = 0.5*( a[:,:-1] + a[:,1:] )
  b[:,0] = a[:,0] + 0.5*( a[:,0] - a[:,1] )
  b[:,-1] = a[:,-1] + 0.5*( a[:,-1] - a[:,-2] )
  return b


def expandJ(a):
  """
  Expands an array by one row, averaging the data to the middle columns and
  extrapolating for the first and last rows. Needed for shifting coordinates
  from centers to corners.
  """
  nj, ni = a.shape
  b = numpy.zeros((nj+1, ni))
  b[1:-1,:] = 0.5*( a[:-1,:] + a[1:,:] )
  b[0,:] = a[0,:] + 0.5*( a[0,:] - a[1,:] )
  b[-1,:] = a[-1,:] + 0.5*( a[-1,:] - a[-2,:] )
  return b


def expand(a):
  """
  Expands a vector by one element, averaging the data to the middle columns and
  extrapolating for the first and last rows. Needed for shifting coordinates
  from centers to corners.
  """
  b = numpy.zeros((len(a)+1))
  b[1:-1] = 0.5*( a[:-1] + a[1:] )
  b[0] = a[0] + 0.5*( a[0] - a[1] )
  b[-1] = a[-1] + 0.5*( a[-1] - a[-2] )
  return b


def boundaryStats(a):
  """
  Returns the minimum and maximum values of a only on the boundaries of the array.
  """
  amin = numpy.amin(a[0,:])
  amin = min(amin, numpy.amin(a[1:,-1]))
  amin = min(amin, numpy.amin(a[-1,:-1]))
  amin = min(amin, numpy.amin(a[1:-1,0]))
  amax = numpy.amax(a[0,:])
  amax = max(amax, numpy.amax(a[1:,-1]))
  amax = max(amax, numpy.amax(a[-1,:-1]))
  amax = max(amax, numpy.amax(a[1:-1,0]))
  return amin, amax


def setFigureSize(aspect=None, verticalResolution=None, nPanels=1, debug=False):
  """
  Set the figure size based on vertical resolution and aspect ratio (tuple of W,H).
  """
  if aspect==None: aspect = {1:[16,9], 2:[1,1], 3:[6,10]}[nPanels]
  if verticalResolution==None: verticalResolution = {1:576, 2:720, 3:1200}[nPanels]
  width = int(1.*aspect[0]/aspect[1] * verticalResolution) # First guess
  if debug: print 'setFigureSize: first guess width =',width
  width = width + ( width % 2 ) # Make even
  if debug: print 'setFigureSize: corrected width =',width
  if debug: print 'setFigureSize: height =',verticalResolution
  plt.figure(figsize=(width/100., verticalResolution/100.)) # 100 dpi always?
  if nPanels==1: plt.gcf().subplots_adjust(left=.08, right=.99, wspace=0, bottom=.09, top=.9, hspace=0)
  elif nPanels==2: plt.gcf().subplots_adjust(left=.11, right=.94, wspace=0, bottom=.05, top=.94, hspace=0.15)
  elif nPanels==3: plt.gcf().subplots_adjust(left=.11, right=.94, wspace=0, bottom=.05, top=.94, hspace=0.15)
  elif nPanels==0: pass
  else: raise Exception('nPanels out of range')


def label(label, units):
  """
  Combines a label string and units string together in the form 'label [units]'
  unless one of the other is empty.
  """
  string = unicode(label)
  if len(units)>0: string = string + ' [' + unicode(units) + ']'
  return string


def createXYlabels(x, y, xLabel, xUnits, yLabel, yUnits):
  """
  Checks that x and y labels are appropriate and tries to make some if they are not.
  """
  if x==None:
    if xLabel==None: xLabel='i'
    if xUnits==None: xUnits=''
  else:
    if xLabel==None: xLabel=u'Longitude'
    if xUnits==None: xUnits=u'\u00B0E'
  if y==None:
    if yLabel==None: yLabel='j'
    if yUnits==None: yUnits=''
  else:
    if yLabel==None: yLabel=u'Latitude'
    if yUnits==None: yUnits=u'\u00B0N'
  return xLabel, xUnits, yLabel, yUnits


def yzplot(field, y=None, z=None,
  yLabel=None, yUnits=None, zLabel=None, zUnits=None,
  title='', suptitle='', nBins=None, cLim=None, landColor=[.5,.5,.5], colormap=None, extend=None,
  aspect=[16,9], resolution=576, newFigure=True,
  ignore=None, save=None, debug=False, show=False, interactive=False):
  """
  Renders section plot of scalar field, field(x,z).

  Arguments:
  field       Scalar 2D array to be plotted.
  y           y (or x) coordinate (1D array). If y is the same size as field then x is treated as
              the cell center coordinates.
  z           z coordinate (1D or 2D array). If z is the same size as field then y is treated as
              the cell center coordinates.
  xLabel      The label for the x axis. Default 'Latitude'.
  xUnits      The units for the x axis. Default 'degrees N'.
  zLabel      The label for the z axis. Default 'Elevation'.
  zUnits      The units for the z axis. Default 'm'.
  title       The title to place at the top of the panel. Default ''.
  suptitle    The super-title to place at the top of the figure. Default ''.
  nBins       The number of colors levels (used is cLim is missing or only specifies the color range).
  cLim        A tuple of (min,max) color range OR a list of contour levels. Default None.
  landColor   An rgb tuple to use for the color of land (no data). Default [.5,.5,.5].
  colormap    The name of the colormap to use. Default None.
  extend      Can be one of 'both', 'neither', 'max', 'min'. Default None.
  aspect      The aspect ratio of the figure, given as a tuple (W,H). Default [16,9].
  resolution  The vertical rseolutin of the figure given in pixels. Default 720.
  ignore      A value to use as no-data (NaN). Default None.
  save        Name of file to save figure in. Default None.
  debug       If true, report sutff for debugging. Default False.
  show        If true, causes the figure to appear on screen. Used for testing. Default False.
  interactive If true, adds interactive features such as zoom, close and cursor. Default False.
  """

  # Create coordinates if not provided
  yLabel, yUnits, zLabel, zUnits = createYZlabels(y, z, yLabel, yUnits, zLabel, zUnits)
  if debug: print 'y,z label/units=',yLabel,yUnits,zLabel,zUnits
  if len(y)==z.shape[-1]: y = expand(y)
  elif len(y)==z.shape[-1]+1: y = y
  else: raise Exception('Length of y coordinate should be equal or 1 longer than horizontal length of z')
  if ignore!=None: maskedField = numpy.ma.masked_array(field, mask=[field==ignore])
  else: maskedField = field.copy()
  yCoord, zCoord, field2 = m6toolbox.section2quadmesh(y, z, maskedField)

  # Diagnose statistics
  sMin, sMax, sMean, sStd, sRMS = myStats(maskedField, yzWeight(y, z), debug=debug)
  yLims = numpy.amin(yCoord), numpy.amax(yCoord)
  zLims = boundaryStats(zCoord)

  # Choose colormap
  if nBins==None and (cLim==None or len(cLim)==2): nBins=35
  if colormap==None: colormap = chooseColorMap(sMin, sMax)
  cmap, norm, extend = chooseColorLevels(sMin, sMax, colormap, cLim=cLim, nBins=nBins, extend=extend)

  if newFigure: setFigureSize(aspect, resolution, debug=debug)
  #plt.gcf().subplots_adjust(left=.10, right=.99, wspace=0, bottom=.09, top=.9, hspace=0)
  axis = plt.gca()
  plt.pcolormesh(yCoord, zCoord, field2, cmap=cmap, norm=norm)
  if interactive: addStatusBar(yCoord, zCoord, field2)
  plt.colorbar(fraction=.08, pad=0.02, extend=extend)
  plt.gca().set_axis_bgcolor(landColor)
  plt.xlim( yLims )
  plt.ylim( zLims )
  axis.annotate('max=%.5g\nmin=%.5g'%(sMax,sMin), xy=(0.0,1.01), xycoords='axes fraction', verticalalignment='bottom', fontsize=10)
  if sMean!=None:
    axis.annotate('mean=%.5g\nrms=%.5g'%(sMean,sRMS), xy=(1.0,1.01), xycoords='axes fraction', verticalalignment='bottom', horizontalalignment='right', fontsize=10)
    axis.annotate(' sd=%.5g\n'%(sStd), xy=(1.0,1.01), xycoords='axes fraction', verticalalignment='bottom', horizontalalignment='left', fontsize=10)
  if len(yLabel+yUnits)>0: plt.xlabel(label(yLabel, yUnits))
  if len(zLabel+zUnits)>0: plt.ylabel(label(zLabel, zUnits))
  if len(title)>0: plt.title(title)
  if len(suptitle)>0: plt.suptitle(suptitle)

  if save!=None: plt.savefig(save)
  if interactive: addInteractiveCallbacks()
  if show: plt.show(block=False)


def yzcompare(field1, field2, y=None, z=None,
  yLabel=None, yUnits=None, zLabel=None, zUnits=None,
  title1='', title2='', title3='A - B', addPlabel=True, suptitle='',
  nBins=None, cLim=None, dLim=None, landColor=[.5,.5,.5], colormap=None, dcolormap=None, extend=None,
  aspect=None, resolution=None, nPanels=3,
  ignore=None, save=None, debug=False, show=False, interactive=False):
  """
  Renders n-panel plot of two scalar fields, field1(x,y) and field2(x,y).

  Arguments:
  field1      Scalar 2D array to be plotted and compared to field2.
  field2      Scalar 2D array to be plotted and compared to field1.
  y           y coordinate (1D array). If y is the same size as field then y is treated as
              the cell center coordinates.
  z           z coordinate (1D or 2D array). If z is the same size as field then z is treated as
              the cell center coordinates.
  yLabel      The label for the y axis. Default 'Latitude'.
  yUnits      The units for the y axis. Default 'degrees N'.
  zLabel      The label for the z axis. Default 'Elevation'.
  zUnits      The units for the z axis. Default 'm'.
  title1      The title to place at the top of panel 1. Default ''.
  title2      The title to place at the top of panel 1. Default ''.
  title3      The title to place at the top of panel 1. Default 'A-B'.
  addPlabel   Adds a 'A:' or 'B:' to the title1 and title2. Default True.
  suptitle    The super-title to place at the top of the figure. Default ''.
  nBins       The number of colors levels (used is cLim is missing or only specifies the color range).
  cLim        A tuple of (min,max) color range OR a list of contour levels for the field plots. Default None.
  dLim        A tuple of (min,max) color range OR a list of contour levels for the difference plot. Default None.
  landColor   An rgb tuple to use for the color of land (no data). Default [.5,.5,.5].
  colormap    The name of the colormap to use for the field plots. Default None.
  dcolormap   The name of the colormap to use for the differece plot. Default None.
  extend      Can be one of 'both', 'neither', 'max', 'min'. Default None.
  aspect      The aspect ratio of the figure, given as a tuple (W,H). Default [16,9].
  resolution  The vertical rseolutin of the figure given in pixels. Default 1280.
  nPanels     Number of panels to display (1, 2 or 3). Default 3.
  ignore      A value to use as no-data (NaN). Default None.
  save        Name of file to save figure in. Default None.
  debug       If true, report sutff for debugging. Default False.
  show        If true, causes the figure to appear on screen. Used for testing. Default False.
  interactive If true, adds interactive features such as zoom, close and cursor. Default False.
  """

  if (field1.shape)!=(field2.shape): raise Exception('field1 and field2 must be the same shape')

  # Create coordinates if not provided
  yLabel, yUnits, zLabel, zUnits = createYZlabels(y, z, yLabel, yUnits, zLabel, zUnits)
  if debug: print 'y,z label/units=',yLabel,yUnits,zLabel,zUnits
  if len(y)==z.shape[-1]: y= expand(y)
  elif len(y)==z.shape[-1]+1: y= y
  else: raise Exception('Length of y coordinate should be equal or 1 longer than horizontal length of z')
  if ignore!=None: maskedField1 = numpy.ma.masked_array(field1, mask=[field1==ignore])
  else: maskedField1 = field1.copy()
  yCoord, zCoord, field1 = m6toolbox.section2quadmesh(y, z, maskedField1)

  # Diagnose statistics
  yzWeighting = yzWeight(y, z)
  s1Min, s1Max, s1Mean, s1Std, s1RMS = myStats(maskedField1, yzWeighting, debug=debug)
  if ignore!=None: maskedField2 = numpy.ma.masked_array(field2, mask=[field2==ignore])
  else: maskedField2 = field2.copy()
  yCoord, zCoord, field2 = m6toolbox.section2quadmesh(y, z, maskedField2)
  s2Min, s2Max, s2Mean, s2Std, s2RMS = myStats(maskedField2, yzWeighting, debug=debug)
  dMin, dMax, dMean, dStd, dRMS = myStats(maskedField1 - maskedField2, yzWeighting, debug=debug)
  dRxy = corr(maskedField1 - s1Mean, maskedField2 - s2Mean, yzWeighting)
  s12Min = min(s1Min, s2Min); s12Max = max(s1Max, s2Max)
  xLims = numpy.amin(yCoord), numpy.amax(yCoord); yLims = boundaryStats(zCoord)
  if debug:
    print 's1: min, max, mean =', s1Min, s1Max, s1Mean
    print 's2: min, max, mean =', s2Min, s2Max, s2Mean
    print 's12: min, max =', s12Min, s12Max

  # Choose colormap
  if nBins==None and (cLim==None or len(cLim)==2): cBins=35
  else: cBins=nBins
  if nBins==None and (dLim==None or len(dLim)==2): nBins=35
  if colormap==None: colormap = chooseColorMap(s12Min, s12Max)
  cmap, norm, extend = chooseColorLevels(s12Min, s12Max, colormap, cLim=cLim, nBins=cBins, extend=extend)

  def annotateStats(axis, sMin, sMax, sMean, sStd, sRMS):
    axis.annotate('max=%.5g\nmin=%.5g'%(sMax,sMin), xy=(0.0,1.025), xycoords='axes fraction', verticalalignment='bottom', fontsize=10)
    if sMean!=None:
      axis.annotate('mean=%.5g\nrms=%.5g'%(sMean,sRMS), xy=(1.0,1.025), xycoords='axes fraction', verticalalignment='bottom', horizontalalignment='right', fontsize=10)
      axis.annotate(' sd=%.5g\n'%(sStd), xy=(1.0,1.025), xycoords='axes fraction', verticalalignment='bottom', horizontalalignment='left', fontsize=10)

  if addPlabel: preTitleA = 'A: '; preTitleB = 'B: '
  else: preTitleA = ''; preTitleB = ''

  setFigureSize(aspect, resolution, nPanels, debug=debug)
  #plt.gcf().subplots_adjust(left=.13, right=.94, wspace=0, bottom=.05, top=.94, hspace=0.15)

  if nPanels in [2, 3]:
    plt.subplot(nPanels,1,1)
    plt.pcolormesh(yCoord, zCoord, field1, cmap=cmap, norm=norm)
    if interactive: addStatusBar(yCoord, zCoord, field1)
    plt.colorbar(fraction=.08, pad=0.02, extend=extend)
    plt.gca().set_axis_bgcolor(landColor)
    plt.xlim( xLims ); plt.ylim( yLims )
    annotateStats(plt.gca(), s1Min, s1Max, s1Mean, s1Std, s1RMS)
    plt.gca().set_xticklabels([''])
    if len(zLabel+zUnits)>0: plt.ylabel(label(zLabel, zUnits))
    if len(title1)>0: plt.title(preTitleA+title1)

    plt.subplot(nPanels,1,2)
    plt.pcolormesh(yCoord, zCoord, field2, cmap=cmap, norm=norm)
    if interactive: addStatusBar(yCoord, zCoord, field2)
    plt.colorbar(fraction=.08, pad=0.02, extend=extend)
    plt.gca().set_axis_bgcolor(landColor)
    plt.xlim( xLims ); plt.ylim( yLims )
    annotateStats(plt.gca(), s2Min, s2Max, s2Mean, s2Std, s2RMS)
    if nPanels==2: plt.gca().set_xticklabels([''])
    if len(zLabel+zUnits)>0: plt.ylabel(label(zLabel, zUnits))
    if len(title2)>0: plt.title(preTitleB+title2)

  if nPanels in [1, 3]:
    plt.subplot(nPanels,1,nPanels)
    if dcolormap==None: dcolormap = chooseColorMap(dMin, dMax)
    cmap, norm, extend = chooseColorLevels(dMin, dMax, dcolormap, cLim=dLim, nBins=nBins, extend=extend)
    plt.pcolormesh(yCoord, zCoord, field1 - field2, cmap=cmap, norm=norm)
    if interactive: addStatusBar(yCoord, zCoord, field1 - field2)
    plt.colorbar(fraction=.08, pad=0.02, extend=extend)
    plt.gca().set_axis_bgcolor(landColor)
    plt.xlim( xLims ); plt.ylim( yLims )
    annotateStats(plt.gca(), dMin, dMax, dMean, dStd, dRMS)
    if len(zLabel+zUnits)>0: plt.ylabel(label(zLabel, zUnits))

  plt.gca().annotate(' r(A,B)=%.5g\n'%(dRxy), xy=(1.0,-0.20), xycoords='axes fraction', verticalalignment='bottom', horizontalalignment='center', fontsize=10)
  if len(yLabel+yUnits)>0: plt.xlabel(label(yLabel, yUnits))
  if len(title3)>0: plt.title(title3)
  if len(suptitle)>0: plt.suptitle(suptitle)

  if save!=None: plt.savefig(save)
  if interactive: addInteractiveCallbacks()
  if show: plt.show(block=False)


def createYZlabels(y, z, yLabel, yUnits, zLabel, zUnits):
  """
  Checks that y and z labels are appropriate and tries to make some if they are not.
  """
  if y==None:
    if yLabel==None: yLabel='j'
    if yUnits==None: yUnits=''
  else:
    if yLabel==None: yLabel=u'Latitude'
    if yUnits==None: yUnits=u'\u00B0N'
  if z==None:
    if zLabel==None: zLabel='k'
    if zUnits==None: zUnits=''
  else:
    if zLabel==None: zLabel='Elevation'
    if zUnits==None: zUnits='m'
  return yLabel, yUnits, zLabel, zUnits


def yzWeight(y, z):
  """
  Calculates the wieghts to use when calculating the statistics of a y-z section.

  y(nj+1) is a 1D vector of column edge positions and z(nk+1,nj) is the interface
  elevations of each column. Returns weight(nk,nj).
  """
  dz = z[:-1,:] - z[1:,:]
  return numpy.matlib.repmat(y[1:] - y[:-1], dz.shape[0], 1) * dz

def dunne_rainbow(N=256):
  """
  Spectral/rainbow colormap from John Dunne.
  """
  cdict = {'red': [(0.00, 0.95, 0.95),
                   (0.09, 0.85, 0.85),
                   (0.18, 0.60, 0.60),
                   (0.32, 0.30, 0.30),
                   (0.45, 0.00, 0.00),
                   (0.60, 1.00, 1.00),
                   (0.85, 1.00, 1.00),
                   (1.00, 0.40, 0.00)],

         'green': [(0.00, 0.75, 0.75),
                   (0.09, 0.85, 0.85),
                   (0.18, 0.60, 0.60),
                   (0.32, 0.20, 0.20),
                   (0.45, 0.60, 0.60),
                   (0.60, 1.00, 1.00),
                   (0.73, 0.70, 0.70),
                   (0.85, 0.00, 0.00),
                   (1.00, 0.00, 0.00)],

         'blue':  [(0.00, 1.00, 1.00),
                   (0.32, 1.00, 1.00),
                   (0.45, 0.30, 0.30),
                   (0.60, 0.00, 0.00),
                   (1.00, 0.00, 0.00)]}
  cmap = matplotlib.colors.LinearSegmentedColormap('dunneRainbow', cdict, N=N)
  #cmap.set_under([1,.65,.85]); cmap.set_over([.25,0.,0.])
  #cmap.set_bad('w')
  matplotlib.cm.register_cmap(cmap=cmap)
  return cmap

# Test
if __name__ == '__main__':
  import nccf
  file = 'baseline/19000101.ocean_static.nc'
  D,(y,x),_ = nccf.readVar(file,'depth_ocean')
  y,_,_ = nccf.readVar(file,'geolat')
  x,_,_ = nccf.readVar(file,'geolon')
  area,_,_ = nccf.readVar(file,'area_t')
  xyplot(D, x, y, title='Depth', ignore=0, suptitle='Testing', area=area, cLim=[0, 5500], nBins=12, debug=True, interactive=True, show=True)#, save='fig_test.png')
  xycompare(D, .9*D, x, y, title1='Depth', ignore=0, suptitle='Testing', area=area, nBins=12)#, save='fig_test2.png')
  annual = 'baseline/19000101.ocean_annual.nc'
  monthly = 'baseline/19000101.ocean_month.nc'
  e,(t,z,y,x),_ = nccf.readVar(annual,'e',0,None,None,1100)
  temp,(t,z,y,x),_ = nccf.readVar(monthly,'temp',0,None,None,1100)
  temp2,(t,z,y,x),_ = nccf.readVar(monthly,'temp',11,None,None,1100)
  yzplot(temp, y, e)
  yzcompare(temp, temp2, y, e, interactive=True)
  yzcompare(temp, temp2, y, e, nPanels=2)
  yzcompare(temp, temp2, y, e, nPanels=1)
  plt.show()
