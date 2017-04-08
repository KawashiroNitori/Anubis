/**
 * Created by Nitori on 2017/4/4.
 */
import React from 'react';
import { connect } from 'react-redux';

import i18n from '../../utils/i18n';

const mapStateToProps = (state, ownProps) => ({
    ...ownProps.member,
});

const mapDispatchToProps = (dispatch) => ({
    handleRemoveClick(e, studentId) {
        if (e.target.tagName === 'BUTTON') {
            e.preventDefault();
            return;
        }
        dispatch({
            type: 'STUDENT_REMOVE',
            payload: studentId,
        });
    },
});

@connect(mapStateToProps, mapDispatchToProps)
export default class AttendFormMemberItemContainer extends React.PureComponent {
    render() {
        return (
            <tr>
                <td className="col--name">
                    {this.props.name}
                </td>
                <td className="col--class">
                    {this.props.class}
                </td>
                <td className="col--college">
                    {this.props.college}
                </td>
                <td className="col--toolbar">
                    <button
                        className="link text-red"
                        onClick={(e) => this.props.handleRemoveClick(e, this.props._id)}
                        onKeyDown={(e) => e.preventDefault()}
                    >
                        <span className="icon icon-delete" data-tooltop={i18n('Remove')} />
                    </button>
                </td>
            </tr>
        );
    }
}
