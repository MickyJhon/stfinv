#!/usr/bin/env python
# -*- coding: utf-8 -*-

# -------------------------------------------------------------------
#   Filename:  plotting.py
#   Purpose:   Provide routines for plotting
#   Author:    Simon Staehler
#   Email:     mail@simonstaehler.com
#   License:   GNU Lesser General Public License, Version 3
# -------------------------------------------------------------------

import matplotlib.pyplot as plt
import os
import numpy as np
from obspy.imaging.beachball import beach
from obspy.geodetics.base import locations2degrees
import matplotlib.patheffects as PathEffects
from matplotlib.colorbar import Colorbar
from matplotlib.cm import get_cmap
from matplotlib.ticker import MaxNLocator
import cartopy.crs as ccrs


def plot_waveforms(st_data, st_synth, arr_times, CC, CClim, dA, dT, stf, depth,
                   origin, tensor, iteration=-1, misfit=0.0,
                   outdir='./waveforms/'):

    if not os.path.exists(outdir):
        os.mkdir(outdir)

    fig = plt.figure(figsize=(15, 10))

    # Axis for the waveforms
    ax = fig.add_subplot(111)

    # Axis for the Source Time Function
    left, bottom, width, height = [0.75, 0.455, 0.14, 0.18]
    ax_stf = fig.add_axes([left, bottom, width, height])

    # Axis for the Beachball
    left, bottom, width, height = [0.75, 0.65, 0.14, 0.14]
    ax_bb = fig.add_axes([left, bottom, width, height])

    # Rectangle for the global map plot. Axis is created later
    rect_stf = [0.75, 0.155, 0.14, 0.25]

    nplots = len(st_data)
    nrows = int(np.sqrt(nplots)) + 1
    ncols = nplots / nrows + 1
    iplot = 0
    st_data_plot = st_data.copy()
    st_data_plot.sort(keys=['azi'])
    for tr in st_data_plot:

        irow = np.mod(iplot, nrows)
        icol = np.int(iplot / nrows)

        normfac = max(np.abs(tr.data))

        yoffset = irow * 1.5
        xoffset = icol

        code = '%s.%s' % (tr.stats.station, tr.stats.location)
        if CC[code] > CClim:
            ls = '-'
        else:
            ls = 'dotted'

        # Plot data
        yvals = tr.data / normfac
        xvals = np.linspace(0, 0.8, num=len(yvals))
        l_d, = ax.plot(xvals + xoffset,
                       yvals + yoffset,
                       color='k',
                       linestyle=ls,
                       linewidth=2.0)

        # Plot Green's function
        yvals = st_synth.select(station=tr.stats.station)[0].data / normfac
        xvals = np.linspace(0, 0.8, num=len(yvals))
        l_g, = ax.plot(xvals + xoffset,
                       yvals + yoffset,
                       color='grey',
                       linestyle=ls,
                       linewidth=1)

        # Convolve with STF and plot synthetics
        yvals = np.convolve(st_synth.select(station=tr.stats.station)[0].data,
                            stf, mode='full')[0:tr.stats.npts] / normfac
        xvals = np.linspace(0, 0.8, num=len(yvals))
        l_s, = ax.plot(xvals + xoffset,
                       yvals + yoffset,
                       color='r',
                       linestyle=ls,
                       linewidth=1.5)

        ax.text(xoffset, yoffset + 0.2,
                '%s \nCC: %4.2f\ndA: %4.1f\ndT: %5.1f' % (tr.stats.station,
                                                          CC[code],
                                                          dA[code],
                                                          dT[code]),
                size=8.0, color='darkgreen')

        # Plot picked P arrival time
        xvals = ((arr_times[code] / tr.times()[-1]) * 0.8 + xoffset) * \
            np.ones(2)
        ax.plot(xvals, (yoffset + 0.5, yoffset - 0.5), 'b')

        iplot += 1

    ax.legend((l_s, l_d, l_g), ('synthetic', 'data', 'Green''s fct'))
    ax.set_xlim(0, ncols * 1.2)
    ax.set_ylim(-1.5, nrows * 1.5)
    ax.set_xticks([])
    ax.set_yticks([])

    if (iteration >= 0):
        ax.set_title('Waveform fits, depth: %d m, it: %d, misfit: %9.3e' %
                     (depth, iteration, misfit))

    # Plot STF
    yvals = stf
    xoffset = _dict_mean(dT) * tr.stats.delta
    xvals = tr.stats.delta * np.arange(0, len(yvals)) + xoffset

    ax_stf.plot(xvals, yvals)
    ax_stf.hlines(0, xmin=xvals[0], xmax=xvals[-1], linestyles='--',
                  color='darkgrey')
    ax_stf.set_ylim((-0.3, 1.1))
    ax_stf.set_xlim((xvals[0], xvals[-1]))
    ax_stf.set_xlabel('time / seconds')
    ax_stf.set_yticks([0])
    ax_stf.set_ylabel('Source Time Function')

    # Plot beach ball
    mt = [tensor.m_rr, tensor.m_tt, tensor.m_pp,
          tensor.m_rt, tensor.m_rp, tensor.m_tp]
    b = beach(mt, width=120, linewidth=1, facecolor='r',
              xy=(0, 0), axes=ax_bb)
    ax_bb.add_collection(b)
    ax_bb.set_xlim((-0.1, 0.1))
    ax_bb.set_ylim((-0.1, 0.1))
    ax_bb.set_xticks([])
    ax_bb.set_yticks([])
    ax_bb.axis('off')

    # Plot Map
    plot_map(st_synth, CC, origin.longitude, origin.latitude, fig=fig,
             CClim=CClim,
             rect=rect_stf, colormap='plasma')

    outfile = os.path.join(outdir, 'waveforms_it_%d.png' % iteration)
    fig.savefig(outfile, format='png')
    plt.close(fig)


def plot_map(st_synth, values, central_longitude, central_latitude, CClim,
             colormap='viridis', fig=None, rect=[0.0, 0.0, 1.0, 1.0]):

    # Create array of latitudes, longitudes, CC
    lats = []
    lons = []
    c = []
    names = []
    for tr in st_synth:
        code = '%s.%s' % (tr.stats.station, tr.stats.location)
        lats.append(tr.stats.sac.stla)
        lons.append(tr.stats.sac.stlo)
        c.append(values[code])
        names.append(code)

    ax = add_ortho(lats=lats, lons=lons, colors=c, CClim=CClim,
                   text=None, marker=['o', 'd'],
                   colormap=colormap, fig=fig, rect=rect,
                   central_longitude=central_longitude,
                   central_latitude=central_latitude)

    return ax


def add_ortho(lats, lons, colors, CClim,
              central_longitude, central_latitude,
              text=None, size=50, marker=['o', 'd'],
              colormap='viridis', fig=None,
              rect=[0.0, 0.0, 1.0, 1.0]):
    if not fig:
        fig = plt.figure()

    proj = ccrs.Orthographic(central_longitude=central_longitude,
                             central_latitude=central_latitude)

    # left, bottom, width, height
    ax = fig.add_axes([rect[0],
                       rect[1] + rect[3] * 0.12,
                       rect[2],
                       rect[3] * 0.85],
                      projection=proj)
    cm_ax = fig.add_axes([rect[0],
                          rect[1],
                          rect[2],
                          rect[3] * 0.08])
    plt.sca(ax)

    # make the map global rather than have it zoom in to
    # the extents of any plotted data
    ax.set_global()

    ax.stock_img()
    ax.coastlines()
    ax.gridlines()

    lats_mark1 = []
    lons_mark1 = []
    colors_mark1 = []
    lats_mark2 = []
    lons_mark2 = []
    colors_mark2 = []

    cmap = get_cmap(colormap)
    cmap.set_under('grey')

    for lon, lat, color in zip(lons, lats, colors):
        if color > CClim:
            lats_mark1.append(lat)
            lons_mark1.append(lon)
            colors_mark1.append(color)
        else:
            lats_mark2.append(lat)
            lons_mark2.append(lon)
            colors_mark2.append(color)

    if len(lons_mark1) > 0:
        scatter = ax.scatter(lons_mark1, lats_mark1, s=size, c=colors_mark1,
                             marker=marker[0],
                             cmap=cmap, vmin=CClim, vmax=1, zorder=10,
                             transform=ccrs.Geodetic())

    if len(lons_mark2) > 0:
        scatter = ax.scatter(lons_mark2, lats_mark2, s=size, c=colors_mark2,
                             marker=marker[1],
                             cmap=cmap, vmin=CClim, vmax=1, zorder=10,
                             transform=ccrs.Geodetic())

    locator = MaxNLocator(5)

    cb = Colorbar(cm_ax, scatter, cmap=cmap,
                  orientation='horizontal',
                  ticks=locator,
                  extend='min')
    cb.set_label('CC')
    # Compat with old matplotlib versions.
    if hasattr(cb, "update_ticks"):
        cb.update_ticks()

    ax.plot(central_longitude, central_latitude, color='red', marker='*',
            markersize=np.sqrt(size))

    if (text):
        for lat, lon, text in zip(lats, lons, text):
            # Avoid plotting invisible texts. They clutter at the origin
            # otherwise
            dist = locations2degrees(lat, lon,
                                     central_latitude, central_longitude)
            if (dist < 90):
                plt.text(lon, lat, text, weight="heavy",
                         transform=ccrs.Geodetic(),
                         color="k", zorder=100,
                         path_effects=[
                             PathEffects.withStroke(linewidth=3,
                                                    foreground="white")])

    return ax


def _dict_mean(dictionary):
    x = np.zeros(len(dictionary))
    i = 0
    for key, value in dictionary.items():
        x[i] = value
        i += 1

    return np.mean(x)
