import collections
import itertools
import math
import typing

import torch

from . import _dev_utils, normalization, pooling

# Add types where possible and ensure torch jit compatibility


class Conv(_dev_utils.modules.InferDimension):
    """Standard convolution layer.

    Based on input shape it either creates 1D, 2D or 3D convolution for inputs of shape
    3D, 4D, 5D respectively (including batch as first dimension).

    Additional `same` `padding` mode was added and set as default.
    This mode preserves all dimensions excepts channels.

    **IMPORTANT**: `same` currently works only for odd values of `kernel_size`,
    `dilation` and `stride`. If any of those is even you should explicitly pad
    your input asymmetrically with `torch.functional.pad` or a-like.

    `kernel_size` got a default value of `3`.

    Otherwise acts exactly like PyTorch's Convolution, see
    `documentation <https://pytorch.org/docs/stable/nn.html#convolution-layers>`__.

    Parameters
    ----------
    in_channels : int
        Number of channels in the input image
    out_channels : int
        Number of channels produced by the convolution
    kernel_size : Union[int, Tuple[int, int], Tuple[int, int, int]], optional
        Size of the convolving kernel. User can specify `int` or 2-tuple (for `Conv2d`)
        or 3-tuple (for `Conv3d`). Default: `3`
    stride : Union[int, Tuple[int, int], Tuple[int, int, int]], optional
        Stride of the convolution. User can specify `int` or 2-tuple (for `Conv2d`)
        or 3-tuple (for `Conv3d`). Default: `3`
    padding : Union[str, int, Tuple[int, int], Tuple[int, int, int]], optional
        Padding added to both sides of the input. String "same" can be used with odd
        `kernel_size`, `stride` and `dilation`
        User can specify `int` or 2-tuple (for `Conv2d`)
        or 3-tuple (for `Conv3d`). Default: `same`
    padding_mode : string, optional
        Accepted values `zeros` and `circular` Default: `zeros`
    dilation : Union[int, Tuple[int, int], Tuple[int, int, int]], optional
        Spacing between kernel elements. String "same" can be used with odd
        `kernel_size`, `stride` and `dilation`
        User can specify `int` or 2-tuple (for `Conv2d`)
        or 3-tuple (for `Conv3d`). Default: `1`
    groups : int, optional
        Number of blocked connections from input channels to output channels. Default: 1
    bias : bool, optional
        If ``True``, adds a learnable bias to the output. Default: ``True``

    """

    def __init__(
        self,
        in_channels: int,
        out_channels: int,
        kernel_size: typing.Union[
            int, typing.Tuple[int, int], typing.Tuple[int, int, int]
        ] = 3,
        stride: typing.Union[
            int, typing.Tuple[int, int], typing.Tuple[int, int, int]
        ] = 1,
        padding: typing.Union[
            str, int, typing.Tuple[int, int], typing.Tuple[int, int, int]
        ] = "same",
        dilation: typing.Union[
            int, typing.Tuple[int, int], typing.Tuple[int, int, int]
        ] = 1,
        groups: int = 1,
        bias: bool = True,
        padding_mode: str = "zeros",
    ):
        super().__init__(
            instance_creator=Conv._pad,
            in_channels=in_channels,
            out_channels=out_channels,
            kernel_size=kernel_size,
            stride=stride,
            padding=padding,
            dilation=dilation,
            groups=groups,
            bias=bias,
            padding_mode=padding_mode,
        )

    @classmethod
    def _dimension_pad(cls, dimension, kernel_size, stride, dilation):
        if kernel_size % 2 == 0:
            raise ValueError(
                'Only odd kernel size for padding "same" is currently supported.'
            )

        return math.ceil(
            (dimension * stride - dimension + dilation * (kernel_size - 1)) / 2
        )

    @classmethod
    def _expand_if_needed(cls, dimensions, argument):
        if isinstance(argument, collections.abc.Iterable):
            return argument
        return tuple(itertools.repeat(argument, len(dimensions)))

    @classmethod
    def _pad(cls, inputs, inner_class, **kwargs):
        if isinstance(kwargs["padding"], str) and kwargs["padding"].lower() == "same":
            dimensions = inputs.shape[2:]
            paddings = tuple(
                cls._dimension_pad(dimension, kernel_size, stride, dilation)
                for dimension, kernel_size, stride, dilation in zip(
                    dimensions,
                    *[
                        cls._expand_if_needed(dimensions, kwargs[name])
                        for name in ("kernel_size", "stride", "dilation")
                    ],
                )
            )
            kwargs["padding"] = paddings

        return inner_class(**kwargs)


class ConvTranspose(_dev_utils.modules.InferDimension):
    """Standard transposed convolution layer.

    Based on input shape it either creates 1D, 2D or 3D convolution (for inputs of shape
    3D, 4D, 5D including batch as first dimension).

    Otherwise acts exactly like PyTorch's Convolution, see
    `documentation <https://pytorch.org/docs/stable/nn.html#convolution-layers>`__.

    Default argument for `kernel_size` was added equal to `3`.

    Parameters
    ----------
    in_channels : int
        Number of channels in the input image
    out_channels : int
        Number of channels produced by the convolution
    kernel_size : Union[int, Tuple[int, int], Tuple[int, int, int]], optional
        Size of the convolving kernel. User can specify `int` or 2-tuple (for `Conv2d`)
        or 3-tuple (for `Conv3d`). Default: `3`
    stride : Union[int, Tuple[int, int], Tuple[int, int, int]], optional
        Stride of the convolution. User can specify `int` or 2-tuple (for `Conv2d`)
        or 3-tuple (for `Conv3d`). Default: `3`
    padding : Union[str, int, Tuple[int, int], Tuple[int, int, int]], optional
        Padding added to both sides of the input. User can specify `int` or 2-tuple (for `Conv2d`)
        or 3-tuple (for `Conv3d`). Default: `0`
    output_padding : int or tuple, optional
        Additional size added to one side of the output shape. Default: 0
    groups : int, optional
        Number of blocked connections from input channels to output channels. Default: 1
    bias : bool, optional
        If ``True``, adds a learnable bias to the output. Default: ``True``
        dilation (int or tuple, optional): Spacing between kernel elements. Default: 1
    dilation : Union[int, Tuple[int, int], Tuple[int, int, int]], optional
        Spacing between kernel elements. String "same" can be used with odd
        `kernel_size`, `stride` and `dilation`
        User can specify `int` or 2-tuple (for `Conv2d`)
        or 3-tuple (for `Conv3d`). Default: `1`
    padding_mode : string, optional
        Accepted values `zeros` and `circular` Default: `zeros`

    """

    def __init__(
        self,
        in_channels: int,
        out_channels: int,
        kernel_size: typing.Union[
            int, typing.Tuple[int, int], typing.Tuple[int, int, int]
        ] = 3,
        stride: typing.Union[
            int, typing.Tuple[int, int], typing.Tuple[int, int, int]
        ] = 1,
        padding: typing.Union[
            int, typing.Tuple[int, int], typing.Tuple[int, int, int]
        ] = 0,
        output_padding: typing.Union[
            int, typing.Tuple[int, int], typing.Tuple[int, int, int]
        ] = 0,
        groups: int = 1,
        bias: bool = True,
        dilation: typing.Union[
            int, typing.Tuple[int, int], typing.Tuple[int, int, int]
        ] = 1,
        padding_mode="zeros",
    ):
        super().__init__(
            in_channels=in_channels,
            out_channels=out_channels,
            kernel_size=kernel_size,
            stride=stride,
            padding=padding,
            output_padding=output_padding,
            groups=groups,
            bias=bias,
            dilation=dilation,
            padding_mode=padding_mode,
        )


class ChannelShuffle(_dev_utils.modules.Representation):
    """Shuffle output channels from _dev_utils.modules.

    When using group convolution knowledge transfer between next layers is reduced
    (as the same input channels are convolved with the same output channels).

    This layer reshuffles output channels via simple `reshape` in order to mix the representation
    from separate groups and improve knowledge transfer.

    Originally proposed by Xiangyu Zhang et. al in:
    `ShuffleNet: An Extremely Efficient Convolutional Neural Network for Mobile Devices <https://arxiv.org/abs/1707.01083>`__

    Parameters
    ----------
    groups : int
        Number of groups used in the previous convolutional layer.

    """

    def __init__(self, groups: int):
        super().__init__()
        self.groups: int = groups

    def forward(self, inputs):
        return (
            inputs.reshape(inputs.shape[0], self.groups, -1, *inputs.shape[2:])
            .transpose(1, 2)
            .reshape(*inputs.shape)
        )


class ChannelSplit(_dev_utils.modules.Representation):
    """Convenience layer splitting tensor using p.

    Returns two outputs, splitted accordingly to parameters.

    Parameters
    ----------
    p : float
        Percentage of channels to go into first group
    dim : int, optional
        Dimension along which input will be splitted. Default: `1` (channel dimension)

    """

    def __init__(self, p: float, dim: int = 1):
        super().__init__()
        if not 0.0 < p < 1.0:
            raise ValueError(
                "Ratio of small expand fire module has to be between 0 and 1."
            )

        self.p: float = p
        self.dim: int = dim

    def forward(self, inputs):
        return torch.split(inputs, int(inputs.shape[1] * self.p), dim=self.dim)


class Residual(torch.nn.Module):
    """Residual connection adding input to output of provided module.

    Originally proposed by He et. al in `ResNet <www.arxiv.org/abs/1512.03385>`__

    For correct usage it is advised to keep input line (skip connection) without
    any layer or activation and implement transformations only in module arguments
    (as per https://arxiv.org/pdf/1603.05027.pdf).

    Above can be easily achieved by using one of BatchNormConv competitorch _dev_utils.modules.

    Parameters
    ----------
    module : torch.nn.Module
        Convolutional PyTorch module (or other compatible module).
        Shape of module's `inputs` has to be equal to it's `outputs`, both
        should be addable `torch.Tensor` instances.
    projection : torch.nn.Module, optional
        If shapes of `inputs` and `module` results are different, it's user
        responsibility to add custom `projection` module (usually `1x1` convolution).
        Default: `None`

    """

    def __init__(self, module: torch.nn.Module, projection: torch.nn.Module = None):
        super().__init__()
        self.module: torch.nn.Module = module
        self.projection: torch.nn.Module = projection

    def forward(self, inputs):
        output = self.module(inputs)
        if self.projection is not None:
            inputs = self.projections(inputs)
        return output + inputs


class Dense(torch.nn.Module):
    """Dense residual connection concatenating input channels and output channels of provided module.

    Originally proposed by Gao Huang et. al in `Densely Connected Convolutional Networks <https://arxiv.org/abs/1608.06993>`__

    Parameters
    ----------
    module : torch.nn.Module
        Convolutional PyTorch module (or other compatible module).
        Shape of module's `inputs` has to be equal to it's `outputs`, both
        should be addable `torch.Tensor` instances.
    dim : int, optional
        Dimension along which `input` and module's `output` will be concatenated.
        Default: `1` (channel-wise)

    """

    def __init__(self, module: torch.nn.Module, dim: int = 1):
        super().__init__()
        self.module: torch.nn.Module = module
        self.dim: int = dim

    def forward(self, inputs):
        return torch.cat(self.module(inputs), inputs, dim=self.dim)


class Poly(torch.nn.Module):
    """Apply one module to input multiple times and sum.

    It's equation for `order` equal to :math:`N` can be written as::

    .. math::
        I + F + F^2 + ... + F^N

    where :math:`I` is identity mapping and :math:`F` is output of `module` applied :math:`^N` times.

    Originally proposed by Xingcheng Zhang et. al in
    `PolyNet: A Pursuit of Structural Diversity in Very Deep Networks <https://arxiv.org/abs/1608.06993>`__

    Parameters
    ----------
    module : torch.nn.Module
        Convolutional PyTorch module (or other compatible module).
        `inputs` shape has to be equal to it's `output` shape
        (for 2D convolution it would be :math:`(C, H, W)`)
    order : int, optional
        Order of PolyInception module. For order equal to `1` acts just like
        ResNet, order of `2` was used in original paper. Default: `2`
    """

    def __init__(self, module: torch.nn.Module, order: int = 2):
        super().__init__()
        if order < 1:
            raise ValueError("Order of Poly cannot be less than 1.")

        self.module: torch.nn.Module = module
        self.order: int = order

    def extra_repr(self):
        return f"order={self.order},"

    def forward(self, inputs):
        outputs = [self.module(inputs)]
        for _ in range(1, self.order):
            outputs.append(self.module(outputs[-1]))
        return torch.stack([inputs] + outputs, dim=0).sum(dim=0)


class MPoly(torch.nn.Module):
    """Apply multiple modules to input multiple times and sum.

    It's equation for `poly_modules` length equal to :math:`N` could be expressed as::

    .. math::
        I + F_0 + F_1(F_0) + ... + F_N(F_{N-1}...F_0)

    where :math:`I` is identity and consecutive :math:`F_N` are consecutive modules
    applied to output of previous ones.

    Originally proposed by Xingcheng Zhang et. al in
    `PolyNet: A Pursuit of Structural Diversity in Very Deep Networks <https://arxiv.org/abs/1608.06993>`__

    Parameters
    ----------
    *poly_modules : torch.nn.Module
        Variable arg of modules to use. If empty, acts as an identity.
        For single module acts like `ResNet`. `2` was used in original paper.
        All modules need `inputs` and `outputs` of equal `shape`.

    """

    def __init__(self, *poly_modules: torch.nn.Module):
        super().__init__()
        self.poly_modules: torch.nn.Module = torch.nn.ModuleList(poly_modules)

    def forward(self, inputs):
        outputs = [self.poly_modules[0](inputs)]
        for module in self.poly_modules[1:]:
            outputs.append(module(outputs[-1]))
        return torch.stack([inputs] + outputs, dim=0).sum(dim=0)


class WayPoly(torch.nn.Module):
    """Apply multiple modules to input and sum.

    It's equation for `poly_modules` length equal to :math:`N` could be expressed as::

    .. math::
        I + F_1(I) + F_2(I) + ... + F_N

    where :math:`I` is identity and consecutive :math:`F_N` are consecutive `poly_modules`
    applied to input.

    Could be considered as an extension of standard `ResNet` to many parallel modules.

    Originally proposed by Xingcheng Zhang et. al in
    `PolyNet: A Pursuit of Structural Diversity in Very Deep Networks <https://arxiv.org/abs/1608.06993>`__

    Parameters
    ----------
    *poly_modules : torch.nn.Module
        Variable arg of modules to use. If empty, acts as an identity.
        For single module acts like `ResNet`. `2` was used in original paper.
        All modules need `inputs` and `outputs` of equal `shape`.
    """

    def __init__(self, *poly_modules: torch.nn.Module):
        super().__init__()
        self.poly_modules: torch.nn.Module = torch.nn.ModuleList(poly_modules)

    def forward(self, inputs):
        outputs = []
        for module in self.poly_modules:
            outputs.append(module(inputs))
        return torch.stack([inputs] + outputs, dim=0).sum(dim=0)


class SqueezeExcitation(_dev_utils.modules.Representation):
    """Learn channel-wise excitation maps for `inputs`.

    Provided `inputs` will be squeezed into `in_channels` via average pooling,
    passed through two non-linear layers, rescaled to :math:`[0, 1]` via `sigmoid`-like function
    and multiplied with original input channel-wise.

    Originally proposed by Xingcheng Zhang et. al in
    `Squeeze-and-Excitation Networks <https://arxiv.org/abs/1709.01507>`__

    Parameters
    ----------
    in_channels : int
        Number of channels in the input
    hidden : int, optional
        Size of the hidden `torch.nn.Linear` layer. Usually smaller than `in_channels`
        (at least in original research paper). Default: `1/16` of `in_channels` as
        suggested by original paper.
    activation : Callable[[Tensor], Tensor], optional
        One argument callable performing activation after hidden layer.
        Default: `torch.nn.ReLU()`
    sigmoid : Callable[[Tensor], Tensor], optional
        One argument callable squashing values after excitation.
        Default: `torch.nn.Sigmoid`

    """

    def __init__(
        self,
        in_channels: int,
        hidden: int = None,
        activation: typing.Callable[[torch.Tensor], torch.Tensor] = None,
        sigmoid: typing.Callable[[torch.Tensor], torch.Tensor] = None,
    ):
        super().__init__()
        self.in_channels: int = in_channels
        self.hidden: int = hidden if hidden is not None else in_channels // 16
        self.activation: typing.Callable[
            [torch.Tensor], torch.Tensor
        ] = activation if activation is not None else torch.nn.ReLU()
        self.sigmoid: typing.Callable[
            [torch.Tensor], torch.Tensor
        ] = sigmoid if sigmoid is not None else torch.nn.Sigmoid()

        self._pooling = pooling.GlobalAvgPool()
        self._first = torch.nn.Linear(in_channels, self.hidden)
        self._second = torch.nn.Linear(self.hidden, in_channels)

    def forward(self, inputs):
        excitation = self.sigmoid(
            self._second(self.activation(self._first(self._pooling(inputs))))
        )

        return inputs * excitation.view(
            *excitation.shape, *([1] * (len(inputs.shape) - 2))
        )


class Fire(_dev_utils.modules.Representation):
    """Squeeze and Expand number of channels efficiently operation-wise.

    First input channels will be squeezed to `hidden` channels and :math:`1 x 1` convolution.
    After that those will be expanded to `out_channels` partially done by :math:`3 x 3` convolution
    and partially by :math:`1 x 1` convolution (as specified by `p` parameter).

    Originally proposed by Forrest N. Iandola et. al in
    `SqueezeNet: AlexNet-level accuracy with 50x fewer parameters and <0.5MB model size <https://arxiv.org/abs/1602.07360>`__

    Parameters
    ----------
    in_channels : int
        Number of channels in the input
    out_channels : int
        Number of channels produced by Fire module
    hidden_channels : int, optional
        Number of hidden channels (squeeze convolution layer).
        Default: `None` (half of `in_channels`)
    p : float, optional
        Ratio of :math:`1 x 1` convolution taken from total `out_channels`.
        The more, the more :math:`1 x 1` convolution will be used during expanding.
        Default: `0.5` (half of `out_channels`)

    """

    def __init__(
        self, in_channels: int, out_channels: int, hidden_channels=None, p: float = 0.5,
    ):
        super().__init__()
        self.in_channels = in_channels
        self.out_channels = out_channels

        if hidden_channels is None:
            if in_channels >= 16:
                self.hidden_channels = in_channels // 2
            else:
                self.hidden_channels = 8
        else:
            self.hidden_channels = hidden_channels

        if not 0.0 < p < 1.0:
            raise ValueError("Fire's p has to be between 0 and 1, got {}".format(p))

        self.p: float = p

        self.squeeze = Conv(in_channels, self.hidden_channels, kernel_size=1)

        small_out_channels = int(out_channels * self.p)
        self.expand_small = Conv(
            self.hidden_channels, small_out_channels, kernel_size=1
        )
        self.expand_large = Conv(
            self.hidden_channels,
            out_channels - small_out_channels,
            kernel_size=3,
            padding=1,
        )

    def forward(self, inputs):
        squeeze = self.squeeze(inputs)
        return torch.cat(
            (self.expand_small(squeeze), self.expand_large(squeeze)), dim=1
        )


# To test
class InvertedResidualBottleneck(_dev_utils.modules.Representation):
    """Inverted residual block used in MobileNetV2, MNasNet, Efficient Net and other architectures.

    Originally proposed by Mark Sandler et. al in
    `MobileNetV2: Inverted Residuals and Linear Bottlenecks <0.5MB model size <https://arxiv.org/abs/1801.04381>`__

    Expanded with `SqueezeExcitation` after depthwise convolution by Mingxing Tan et. al in
    `MnasNet: Platform-Aware Neural Architecture Search for Mobile <https://arxiv.org/abs/1807.11626>`__

    Due to it's customizable nature blocks from other research papers could be easily produced, e.g.
    `Searching for MobileNetV3 <https://arxiv.org/pdf/1905.02244.pdf>`__ by providing
    `torchlayers.HardSwish()` as `activation`, `torchlayers.HardSigmoid()` as `squeeze_excitation_activation`
    and `squeeze_excitation_hidden` equal to `hidden_channels // 4`.

    Parameters
    ----------
    in_channels: int
        Number of channels in the input
    hidden_channels: int, optional
        Number of hidden channels (expanded). Should be greater than `in_channels`, usually
        by factor of `4`. Default: `in_channels * 4`
    activation: typing.Callable, optional
        One argument callable performing activation after hidden layer.
        Default: `torch.nn.ReLU6()`
    batchnorm: bool, optional
        Whether to apply Batch Normalization layer after initial convolution,
        depthwise expanding part (before squeeze excitation) and final squeeze.
        Default: `True`
    squeeze_excitation: bool, optional
        Whether to use standard `SqueezeExcitation` (see `SqueezeExcitation` module)
        after depthwise convolution.
        Default: `True`
    squeeze_excitation_hidden: int, optional
        Size of the hidden `torch.nn.Linear` layer. Usually smaller than `in_channels`
        (at least in original research paper). Default: `1/16` of `in_channels` as
        suggested by original paper.
    squeeze_excitation_activation: typing.Callable, optional
        One argument callable performing activation after hidden layer.
        Default: `torch.nn.ReLU()`
    squeeze_excitation_sigmoid: typing.Callable, optional
        One argument callable squashing values after excitation.
        Default: `torch.nn.Sigmoid`

    """

    def __init__(
        self,
        in_channels: int,
        hidden_channels: int = None,
        activation: typing.Callable[[torch.Tensor], torch.Tensor] = None,
        batchnorm: bool = True,
        squeeze_excitation: bool = True,
        squeeze_excitation_hidden: int = None,
        squeeze_excitation_activation: typing.Callable[
            [torch.Tensor], torch.Tensor
        ] = None,
        squeeze_excitation_sigmoid: typing.Callable[
            [torch.Tensor], torch.Tensor
        ] = None,
    ):
        def _add_batchnorm(block, channels):
            if batchnorm:
                block.append(normalization.BatchNorm(channels))
            return block

        super().__init__()

        # Argument assignments
        self.in_channels: int = in_channels
        self.hidden_channels: int = hidden_channels if hidden_channels is not None else in_channels * 4
        self.activation: typing.Callable[
            [torch.Tensor], torch.Tensor
        ] = torch.nn.ReLU6() if activation is None else activation
        self.batchnorm: bool = batchnorm
        self.squeeze_excitation: bool = squeeze_excitation
        self.squeeze_excitation_hidden: int = self.squeeze_excitation_hidden
        self.squeeze_excitation_activation: typing.Callable[
            [torch.Tensor], torch.Tensor
        ] = squeeze_excitation_activation
        self.squeeze_excitation_sigmoid: typing.Callable[
            [torch.Tensor], torch.Tensor
        ] = squeeze_excitation_sigmoid

        # Initial expanding block
        initial = torch.nn.Sequential(
            *_add_batchnorm(
                [
                    Conv(self.in_channels, self.hidden_channels, kernel_size=1),
                    self.activation,
                ],
                self.hidden_channels,
            )
        )

        # Depthwise block
        depthwise_modules = _add_batchnorm(
            [
                Conv(
                    self.hidden_channels,
                    self.hidden_channels,
                    kernel_size=3,
                    groups=self.hidden_channels,
                ),
                self.activation,
            ],
            self.hidden_channels,
        )

        if squeeze_excitation:
            depthwise_modules.append(
                SqueezeExcitation(
                    self.hidden_channels,
                    squeeze_excitation_hidden,
                    squeeze_excitation_activation,
                    squeeze_excitation_sigmoid,
                )
            )

        depthwise = torch.nn.Sequential(*depthwise_modules)

        # Squeeze to in channels
        squeeze = torch.nn.Sequential(
            *_add_batchnorm(
                [Conv(self.hidden_channels, self.in_channels, kernel_size=1,),],
                self.in_channels,
            )
        )

        self.block = Residual(torch.nn.Sequential(initial, depthwise, squeeze))

    def forward(self, inputs):
        return self.block(inputs)
