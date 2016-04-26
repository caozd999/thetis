"""
Implements Equation and Term classes.

"""
from utility import *


class Term(object):
    """
    Implements a single term of an equation.
    """
    def __init__(self, function_space):
        # define bunch of members needed to construct forms
        self.function_space = function_space
        self.mesh = self.function_space.mesh()
        self.test = TestFunction(self.function_space)
        self.tri = TrialFunction(self.function_space)
        self.normal = FacetNormal(self.mesh)
        # TODO construct them here from mesh ?
        self.boundary_markers = function_space.mesh().exterior_facets.unique_markers
        self.boundary_len = function_space.mesh().boundary_len

    def residual(self, solution, solution_old, fields, fields_old, bnd_conditions):
        """
        Returns an UFL form of the term.

        Sign convention: all terms are assumed to be on the left hand side of the equation A + term = 0.

        :arg solution: solution :class:`.Function` of the corresponding equation
        :arg solution_old: a time lagged solution :class:`.Function`
        :arg fields: a dictionary that provides all the remaining fields that the term depends on.
            The keys of the dictionary should standard field names in `field_metadata`
        :arg fields_old: Time lagged dictionary of fields
        :arg bnd_conditions: A dictionary describing boundary conditions.
            E.g. {3: {'elev_2d': Constant(1.0)}} replaces elev_2d function by a constant on boundary ID 3.
        """
        raise NotImplementedError('Must be implemented in the derived class')

    def jacobian(self, solution, solution_old, fields, fields_old, bnd_conditions):
        """
        Returns an UFL form of the Jacobian of the term.

        Sign convention: all terms are assumed to be on the left hand side of the equation A + term = 0.

        :arg solution: solution :class:`.Function` of the corresponding equation
        :arg solution_old: a time lagged solution :class:`.Function`
        :arg fields: a dictionary that provides all the remaining fields that the term depends on.
            The keys of the dictionary should standard field names in `field_metadata`
        :arg fields_old: Time lagged dictionary of fields
        :arg bnd_conditions: A dictionary describing boundary conditions.
            E.g. {3: {'elev_2d': Constant(1.0)}} replaces elev_2d function by a constant on boundary ID 3.
        """
        # TODO default behavior: symbolic expression, or implement only if user-defined?
        raise NotImplementedError('Must be implemented in the derived class')


class EquationNew(object):
    """
    Implements an equation, made out of terms.
    """
    SUPPORTED_LABELS = ['source', 'explicit', 'implicit', 'nonlinear']

    def __init__(self, function_space):
        self.terms = {}
        self.labels = {}
        self.function_space = function_space
        self.mesh = self.function_space.mesh()
        self.test = TestFunction(self.function_space)
        self.trial = TrialFunction(self.function_space)
        # mesh dependent variables
        self.normal = FacetNormal(self.mesh)
        self.xyz = SpatialCoordinate(self.mesh)
        self.e_x, self.e_y, self.e_y = unit_vectors(3)

    def mass_term(self, solution):
        """
        Default mass matrix term for the used solution function space.

        Can be overloaded in derived classes if needed.
        """
        return inner(solution, self.test) * dx

    def add_term(self, term, label):
        key = term.__class__.__name__
        self.terms[key] = term
        self.label_term(key, label)

    def label_term(self, key, label):
        """
        Assings a label to the given term(s).

        :arg term: :class:`.Term` object, or a tuple of terms
        :arg label: string label to assign
        """
        if isinstance(key, str):
            assert key in self.terms, 'Unknown term, add it to the equation'
            assert label in self.SUPPORTED_LABELS, 'bad label: {:}'.format(label)
            self.labels[key] = label
        else:
            for k in iter(key):
                self.label_term(k, label)

    def residual(self, label, solution, solution_old, fields, fields_old, bnd_conditions):
        """
        Returns an UFL form of the residual by summing up all the terms with the desired label.

        Sign convention: all terms are assumed to be on the left hand side of the equation A + term = 0.

        :arg label: string defining the type of terms to sum up. Currently one of
            'source'|'explicit'|'implicit'|'nonlinear'. Can be a list of multiple labels, or 'all' in which
            case all defined terms are summed.
        :arg solution: solution :class:`.Function` of the corresponding equation
        :arg solution_old: a time lagged solution :class:`.Function`
        :arg fields: a dictionary that provides all the remaining fields that the term depends on.
            The keys of the dictionary should standard field names in `field_metadata`
        :arg fields_old: Time lagged dictionary of fields
        :arg bnd_conditions: A dictionary describing boundary conditions.
            E.g. {3: {'elev_2d': Constant(1.0)}} replaces elev_2d function by a constant on boundary ID 3.
        """
        if isinstance(label, str):
            if label == 'all':
                labels = self.SUPPORTED_LABELS
            else:
                labels = [label]
        else:
            labels = list(label)
        f = 0
        for key in self.terms:
            if self.labels[key] in labels:
                f += self.terms[key].residual(solution, solution_old, fields, fields_old, bnd_conditions)
        return f

    def jacobian(self, label, solution, solution_old, fields, fields_old, bnd_conditions):
        """
        Returns an UFL form of the Jacobian by summing up all the Jacobians of the terms.

        Sign convention: all terms are assumed to be on the left hand side of the equation A + term = 0.

        :arg label: string defining the type of terms to sum up. Currently one of
            'source'|'explicit'|'implicit'|'nonlinear'. Can be a list of multiple labels, or 'all' in which
            case all defined terms are summed.
        :arg solution: solution :class:`.Function` of the corresponding equation
        :arg solution_old: a time lagged solution :class:`.Function`
        :arg fields: a dictionary that provides all the remaining fields that the term depends on.
            The keys of the dictionary should standard field names in `field_metadata`
        :arg fields_old: Time lagged dictionary of fields
        :arg bnd_conditions: A dictionary describing boundary conditions.
            E.g. {3: {'elev_2d': Constant(1.0)}} replaces elev_2d function by a constant on boundary ID 3.
        """
        if isinstance(label, str):
            if label == 'all':
                labels = self.SUPPORTED_LABELS
            else:
                labels = [label]
        else:
            labels = list(label)
        f = 0
        for key in self.terms:
            if self.labels[key] in labels:
                # FIXME check if jacobian exists?
                f += self.terms[key].jacobian(solution, solution_old, fields, fields_old, bnd_conditions)
        return f
