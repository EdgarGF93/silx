# coding: utf-8
# /*##########################################################################
#
# Copyright (c) 2014-2017 European Synchrotron Radiation Facility
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.
#
# ############################################################################*/
"""
This module provides convenient classes and functions for OpenGL rendering.
"""

__authors__ = ["T. Vincent"]
__license__ = "MIT"
__date__ = "03/04/2017"


import numpy as np
from ...._glutils.gl import *  # noqa


def buildFillMaskIndices(nIndices):
    if nIndices <= np.iinfo(np.uint16).max + 1:
        dtype = np.uint16
    else:
        dtype = np.uint32

    lastIndex = nIndices - 1
    splitIndex = lastIndex // 2 + 1
    indices = np.empty(nIndices, dtype=dtype)
    indices[::2] = np.arange(0, splitIndex, step=1, dtype=dtype)
    indices[1::2] = np.arange(lastIndex, splitIndex - 1, step=-1,
                              dtype=dtype)
    return indices


class Shape2D(object):
    _NO_HATCH = 0
    _HATCH_STEP = 20

    def __init__(self, points, fill='solid', stroke=True,
                 fillColor=(0., 0., 0., 1.), strokeColor=(0., 0., 0., 1.),
                 strokeClosed=True):
        self.vertices = np.array(points, dtype=np.float32, copy=False)
        self.strokeClosed = strokeClosed

        self._indices = buildFillMaskIndices(len(self.vertices))

        tVertex = np.transpose(self.vertices)
        xMin, xMax = min(tVertex[0]), max(tVertex[0])
        yMin, yMax = min(tVertex[1]), max(tVertex[1])
        self.bboxVertices = np.array(((xMin, yMin), (xMin, yMax),
                                      (xMax, yMin), (xMax, yMax)),
                                     dtype=np.float32)
        self._xMin, self._xMax = xMin, xMax
        self._yMin, self._yMax = yMin, yMax

        self.fill = fill
        self.fillColor = fillColor
        self.stroke = stroke
        self.strokeColor = strokeColor

    @property
    def xMin(self):
        return self._xMin

    @property
    def xMax(self):
        return self._xMax

    @property
    def yMin(self):
        return self._yMin

    @property
    def yMax(self):
        return self._yMax

    def prepareFillMask(self, posAttrib):
        glEnableVertexAttribArray(posAttrib)
        glVertexAttribPointer(posAttrib,
                              2,
                              GL_FLOAT,
                              GL_FALSE,
                              0, self.vertices)

        glEnable(GL_STENCIL_TEST)
        glStencilMask(1)
        glStencilFunc(GL_ALWAYS, 1, 1)
        glStencilOp(GL_INVERT, GL_INVERT, GL_INVERT)
        glColorMask(GL_FALSE, GL_FALSE, GL_FALSE, GL_FALSE)
        glDepthMask(GL_FALSE)

        glDrawElements(GL_TRIANGLE_STRIP, len(self._indices),
                       GL_UNSIGNED_SHORT, self._indices)

        glStencilFunc(GL_EQUAL, 1, 1)
        glStencilOp(GL_ZERO, GL_ZERO, GL_ZERO)  # Reset stencil while drawing
        glColorMask(GL_TRUE, GL_TRUE, GL_TRUE, GL_TRUE)
        glDepthMask(GL_TRUE)

    def renderFill(self, posAttrib):
        self.prepareFillMask(posAttrib)

        glVertexAttribPointer(posAttrib,
                              2,
                              GL_FLOAT,
                              GL_FALSE,
                              0, self.bboxVertices)
        glDrawArrays(GL_TRIANGLE_STRIP, 0, len(self.bboxVertices))

        glDisable(GL_STENCIL_TEST)

    def renderStroke(self, posAttrib):
        glEnableVertexAttribArray(posAttrib)
        glVertexAttribPointer(posAttrib,
                              2,
                              GL_FLOAT,
                              GL_FALSE,
                              0, self.vertices)
        glLineWidth(1)
        drawMode = GL_LINE_LOOP if self.strokeClosed else GL_LINE_STRIP
        glDrawArrays(drawMode, 0, len(self.vertices))

    def render(self, posAttrib, colorUnif, hatchStepUnif):
        assert self.fill in ['hatch', 'solid', None]
        if self.fill is not None:
            glUniform4f(colorUnif, *self.fillColor)
            step = self._HATCH_STEP if self.fill == 'hatch' else self._NO_HATCH
            glUniform1i(hatchStepUnif, step)
            self.renderFill(posAttrib)

        if self.stroke:
            glUniform4f(colorUnif, *self.strokeColor)
            glUniform1i(hatchStepUnif, self._NO_HATCH)
            self.renderStroke(posAttrib)


# matrix ######################################################################

def mat4Ortho(left, right, bottom, top, near, far):
    """Orthographic projection matrix (row-major)"""
    return np.matrix((
        (2./(right - left), 0., 0., -(right+left)/float(right-left)),
        (0., 2./(top - bottom), 0., -(top+bottom)/float(top-bottom)),
        (0., 0., -2./(far-near),    -(far+near)/float(far-near)),
        (0., 0., 0., 1.)), dtype=np.float32)


def mat4Translate(x=0., y=0., z=0.):
    """Translation matrix (row-major)"""
    return np.matrix((
        (1., 0., 0., x),
        (0., 1., 0., y),
        (0., 0., 1., z),
        (0., 0., 0., 1.)), dtype=np.float32)


def mat4Scale(sx=1., sy=1., sz=1.):
    """Scale matrix (row-major)"""
    return np.matrix((
        (sx, 0., 0., 0.),
        (0., sy, 0., 0.),
        (0., 0., sz, 0.),
        (0., 0., 0., 1.)), dtype=np.float32)


def mat4Identity():
    """Identity matrix"""
    return np.matrix((
        (1., 0., 0., 0.),
        (0., 1., 0., 0.),
        (0., 0., 1., 0.),
        (0., 0., 0., 1.)), dtype=np.float32)
